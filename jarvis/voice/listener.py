import time
import threading
import queue
import collections
import re
import json
import numpy as np
import sounddevice as sd
import speech_recognition as sr

from jarvis.config import config, DATA_DIR
from jarvis.voice.sfx import play_wake_chime
from jarvis.voice.speaker import speaker


class JarvisListener:
    def __init__(self):
        # Sort wake words longest-first so multi-word variants match before single words
        self.wake_words = sorted(set([w.lower().strip() for w in config.WAKE_WORDS]), key=len, reverse=True)
        self.recognizer = sr.Recognizer()
        
        # Audio device configuration
        self.mic_index, self.sample_rate, self.channels = self._detect_microphone()
        self.dynamic_threshold = 25
        self.interruption_threshold = 1200
        
        # Runtime states
        self.is_paused = False
        self._stop_requested = False
        self.state = "STANDBY"
        self._processing = False
        
        # Continuous Conversation Mode
        self.in_conversation = False
        self.conversation_expiry = 0.0
        self.CONVERSATION_TIMEOUT = 15.0
        
        # VAD & Endpointing timing — comfortable conversational pace!
        self.SILENCE_TIMEOUT_STANDBY = 0.85  # 850ms for wake word + command
        self.SILENCE_TIMEOUT_CONVO = 0.90    # 900ms in conversation
        self.max_speech_duration = 15.0
        self.blocksize = int(self.sample_rate * 0.032)
        if self.blocksize < 256:
            self.blocksize = 512
            
        # Rolling pre-buffer
        self.pre_buffer = collections.deque(maxlen=int(0.40 * self.sample_rate / self.blocksize))
        self.audio_queue = queue.Queue()
        
        # Callbacks
        self.on_state_change = []
        self.on_wake_word_detected = []
        self.on_command_detected = []
        self.on_sound_level = []

        # Vosk offline speech recognizer (instant, no network)
        self._vosk_model = None
        self._vosk_available = False
        self._init_vosk()

        # Connect speaker stop event to refresh conversation window
        speaker.register_callback(on_stop=self._on_speaker_finished)

    def _init_vosk(self):
        """Initialize Vosk offline speech model for instant local recognition."""
        try:
            from vosk import Model, SetLogLevel
            SetLogLevel(-1)  # silence vosk logs
            model_path = str(DATA_DIR / "vosk-model-small-en-us-0.15")
            import os
            if os.path.exists(model_path):
                self._vosk_model = Model(model_path)
                self._vosk_available = True
                print("[Listener] Vosk offline STT loaded - instant local recognition active!")
            else:
                print("[Listener] Vosk model not found. Using Google Web STT (slower, needs internet).")
        except ImportError:
            print("[Listener] Vosk not installed. Using Google Web STT only.")
        except Exception as e:
            print(f"[Listener] Vosk init error: {e}. Using Google Web STT only.")

    def _vosk_transcribe(self, pcm_mono_int16: np.ndarray) -> str:
        """Instant local transcription using Vosk. No network. ~50-200ms."""
        if not self._vosk_available or self._vosk_model is None:
            return ""
        try:
            from vosk import KaldiRecognizer
            rec = KaldiRecognizer(self._vosk_model, self.sample_rate)
            rec.SetWords(True)
            
            pcm_bytes = pcm_mono_int16.astype(np.int16).tobytes()
            rec.AcceptWaveform(pcm_bytes)
            result = json.loads(rec.FinalResult())
            text = result.get("text", "").strip()
            return text
        except Exception as e:
            print(f"[Vosk Error] {e}")
            return ""

    def _on_speaker_finished(self):
        """When Mani finishes speaking, refresh the conversation timer."""
        if self.in_conversation and not self._stop_requested:
            self.conversation_expiry = time.time() + self.CONVERSATION_TIMEOUT
            if self.state != "PROCESSING":
                self._set_state("CONVERSATION")

    def _detect_microphone(self) -> tuple[int | None, int, int]:
        """Detect working microphone. Prefers 16kHz mono for Vosk/STT compatibility."""
        target_idx = config.MIC_INDEX
        if target_idx is None:
            default_dev = sd.default.device
            if default_dev[0] is not None and default_dev[0] >= 0:
                target_idx = int(default_dev[0])

        # Prefer 16kHz mono (optimal for Vosk and Google STT)
        for sr_try in [16000, 44100, 48000]:
            try:
                sd.check_input_settings(device=target_idx, channels=1, samplerate=sr_try, dtype='int16')
                dev = sd.query_devices(target_idx) if target_idx is not None else sd.query_devices(sd.default.device[0])
                name = dev.get("name", "Default Mic") if dev else "Default Mic"
                print(f"[Listener] Microphone: '{name}' @ {sr_try}Hz, 1ch mono")
                return target_idx, sr_try, 1
            except Exception:
                continue

        # Final fallback
        try:
            if target_idx is not None:
                dev = sd.query_devices(target_idx)
                sr_val = int(dev.get("default_samplerate", 44100))
                ch_val = min(int(dev.get("max_input_channels", 2)), 2)
                if ch_val < 1: ch_val = 1
                print(f"[Listener] Microphone fallback: {sr_val}Hz, {ch_val}ch")
                return target_idx, sr_val, ch_val
        except Exception as e:
            print(f"[Listener Warning] {e}")
        return None, config.SAMPLE_RATE, 1

    def calibrate_ambient_noise(self, duration: float = 0.6):
        """Measure ambient noise level to set an adaptive speech trigger threshold."""
        try:
            samples = int(duration * self.sample_rate)
            rec = sd.rec(samples, samplerate=self.sample_rate, channels=self.channels, dtype='int16', device=self.mic_index)
            sd.wait()
            mono = rec.flatten()
            ambient_rms = float(np.sqrt(np.mean(mono.astype(np.float32)**2)))
            
            # Robust adaptive threshold: avoid triggering on minor ambient hum/fan noise
            self.dynamic_threshold = max(int(ambient_rms * 1.4 + 35), 100)
            self.interruption_threshold = max(int(self.dynamic_threshold * 2.2), 320)
            print(f"[Listener] Ambient RMS: {ambient_rms:.1f} | Speech Threshold: {self.dynamic_threshold} | Interruption: {self.interruption_threshold}")
        except Exception as e:
            self.dynamic_threshold = 100
            self.interruption_threshold = 320
            print(f"[Listener] Calibration fallback: {e}")

    def register_callback(self, on_state_change=None, on_wake=None, on_command=None, on_sound_level=None):
        if on_state_change:
            self.on_state_change.append(on_state_change)
        if on_wake:
            self.on_wake_word_detected.append(on_wake)
        if on_command:
            self.on_command_detected.append(on_command)
        if on_sound_level:
            self.on_sound_level.append(on_sound_level)

    def _set_state(self, new_state: str):
        self.state = new_state
        for cb in self.on_state_change:
            try:
                cb(new_state)
            except Exception:
                pass

    def start_conversation(self, duration: float | None = None):
        """Initiates Continuous Conversation Mode."""
        dur = duration or self.CONVERSATION_TIMEOUT
        self.in_conversation = True
        self.conversation_expiry = time.time() + dur
        if self.state not in ("PROCESSING", "SPEAKING", "LISTENING"):
            self._set_state("CONVERSATION")
        print(f"[{config.ASSISTANT_NAME}] >> Conversation mode ACTIVE ({dur:.0f}s)")

    def refresh_conversation(self, duration: float | None = None):
        """Refreshes the active conversation window."""
        dur = duration or self.CONVERSATION_TIMEOUT
        self.in_conversation = True
        self.conversation_expiry = time.time() + dur
        if self.state not in ("PROCESSING", "SPEAKING", "LISTENING"):
            self._set_state("CONVERSATION")

    def end_conversation(self):
        """Exits Continuous Conversation Mode."""
        was_active = self.in_conversation
        self.in_conversation = False
        self.conversation_expiry = 0.0
        self._set_state("STANDBY")
        if was_active:
            print(f"[{config.ASSISTANT_NAME}] >> Conversation OFF. Standing by.")

    def check_wake_word(self, text: str) -> tuple[bool, str]:
        """Check if text contains wake word and extract clean command."""
        clean = text.lower().strip(" ,.?!")
        if not clean:
            return False, ""

        # 1. Exact match against configured wake words
        for w in self.wake_words:
            if clean == w:
                return True, ""

        # 2. Leading wake word with separator
        for w in self.wake_words:
            for sep in [" ", ",", ":", ";"]:
                prefix = w + sep
                if clean.startswith(prefix):
                    return True, clean[len(prefix):].strip(" ,.?!:")

        # 3. Trailing wake word
        for w in self.wake_words:
            suffix = " " + w
            if clean.endswith(suffix):
                return True, clean[:-len(suffix)].strip(" ,.?!:")

        # 4. In-sentence pattern " ... mani ... " or " ... മാണി ... "
        for w in self.wake_words:
            pattern = f" {w} "
            padded = f" {clean} "
            if pattern in padded:
                parts = padded.split(pattern, 1)
                p0 = parts[0].strip(" ,.?!:")
                p1 = parts[1].strip(" ,.?!:")
                p0 = re.sub(r'^(?:hey|he|hi|hello|okay|ok|yo|ഹേയ്|ഹലോ)\s*', '', p0).strip(" ,.?!:")
                cmd = f"{p0} {p1}".strip()
                return True, cmd

        # 5. Regex catch-all for phonetic prefixes like "he money", "a money", "ഹേയ് മാണി"
        m_start = re.match(r'^(?:hey|he|hi|hello|okay|ok|wake up|yo|a|ഹേയ്|ഹലോ)?\s*(?:mani|money|many|manny|jarvis|മാണി|മണി|മാനി)\s*[,:]?\s*(.*)$', clean, re.IGNORECASE)
        if m_start:
            return True, m_start.group(1).strip(" ,.?!:")

        m_end = re.match(r'^(.*?)\s*[,:]?\s*(?:hey|he|hi|hello|okay|ok|ഹേയ്|ഹലോ)?\s*(?:mani|money|many|manny|jarvis|മാണി|മണി|മാനി)$', clean, re.IGNORECASE)
        if m_end:
            return True, m_end.group(1).strip(" ,.?!:")

        return False, ""

    @staticmethod
    def _normalize_audio(pcm_array: np.ndarray, target_peak: int = 22000) -> np.ndarray:
        """Boost quiet audio to optimal STT level."""
        if len(pcm_array) == 0:
            return pcm_array
        max_val = np.max(np.abs(pcm_array))
        if max_val > 200:
            gain = min(target_peak / max_val, 8.0)
            if gain > 1.2:
                pcm_array = np.clip(pcm_array.astype(np.float32) * gain, -32767, 32767).astype(np.int16)
        return pcm_array

    @staticmethod
    def _normalize_command_text(text: str) -> str:
        """Correct common acoustic/STT misinterpretations (English & Malayalam)."""
        if not text:
            return ""
        t = text.strip()
        # English normalization
        t = re.sub(r'\byou\s*tube\b', 'youtube', t, flags=re.IGNORECASE)
        t = re.sub(r'\bu\s*tube\b', 'youtube', t, flags=re.IGNORECASE)
        t = re.sub(r'\bto\s+tube\b', 'youtube', t, flags=re.IGNORECASE)
        t = re.sub(r'\byour\s+tube\b', 'youtube', t, flags=re.IGNORECASE)
        t = re.sub(r'\bbrowser\s+it\b', 'browser', t, flags=re.IGNORECASE)
        t = re.sub(r'\bgoogle\s+chrome\b', 'chrome', t, flags=re.IGNORECASE)
        t = re.sub(r'\bchrome\s+browser\b', 'chrome', t, flags=re.IGNORECASE)
        t = re.sub(r'\bvs\s+code\b', 'vscode', t, flags=re.IGNORECASE)
        t = re.sub(r'\bvisual\s+studio\s+code\b', 'vscode', t, flags=re.IGNORECASE)

        # Malayalam normalization (മലയാളം)
        t = re.sub(r'\bയൂ\s*റ്റ്യൂബ്\b', 'യൂട്യൂബ്', t)
        t = re.sub(r'\bയൂ\s*ട്യൂബ്\b', 'യൂട്യൂബ്', t)
        t = re.sub(r'\bയുറ്റ്യൂബ്\b', 'യൂട്യൂബ്', t)
        t = re.sub(r'\bയൂടൂബ്\b', 'യൂട്യൂബ്', t)
        return t

    def transcribe(self, pcm_mono_int16: np.ndarray) -> str:
        """
        High-accuracy STT pipeline with bilingual Malayalam & English support:
        1. Primary: Google Web STT using configured AUDIO_LANGUAGE (default ml-IN).
        2. Dual-language fallback: If primary language returns no match, try secondary
           (e.g., if user speaks English while in Malayalam mode, or vice versa).
        3. Fall back to Vosk local model if completely offline.
        """
        if len(pcm_mono_int16) < int(self.sample_rate * 0.25):
            return ""

        t0 = time.time()
        norm_pcm = self._normalize_audio(pcm_mono_int16)
        pcm_bytes = norm_pcm.astype(np.int16).tobytes()
        audio_data = sr.AudioData(pcm_bytes, self.sample_rate, 2)

        primary_lang = config.AUDIO_LANGUAGE or "ml-IN"
        fallback_lang = "en-IN" if primary_lang.startswith("ml") else "ml-IN"

        # 1. Primary: Google Web STT with active language
        try:
            text = self.recognizer.recognize_google(audio_data, language=primary_lang)
            google_ms = (time.time() - t0) * 1000
            if text and text.strip():
                clean_text = self._normalize_command_text(text.strip())
                print(f"[STT Google ({primary_lang})] \"{clean_text}\" ({google_ms:.0f}ms)")
                return clean_text
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print(f"[STT Google Network Error] {e}")
        except Exception as e:
            print(f"[STT Error] {e}")

        # 2. Dual-language fallback: Try secondary language if primary had no match
        try:
            text = self.recognizer.recognize_google(audio_data, language=fallback_lang)
            fallback_ms = (time.time() - t0) * 1000
            if text and text.strip():
                clean_text = self._normalize_command_text(text.strip())
                print(f"[STT Google Fallback ({fallback_lang})] \"{clean_text}\" ({fallback_ms:.0f}ms)")
                return clean_text
        except sr.UnknownValueError:
            pass
        except Exception:
            pass

        # 3. Offline fallback: Vosk local model
        if self._vosk_available:
            vosk_text = self._vosk_transcribe(norm_pcm)
            vosk_ms = (time.time() - t0) * 1000
            if vosk_text and len(vosk_text.strip()) > 1:
                clean_text = self._normalize_command_text(vosk_text)
                print(f"[STT Vosk Fallback] \"{clean_text}\" ({vosk_ms:.0f}ms)")
                return clean_text
            
        return ""

    def _audio_callback(self, indata, frames, time_info, status):
        """Continuous low-latency audio stream callback."""
        if self._stop_requested or self.is_paused:
            return

        mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
        rms = float(np.sqrt(np.mean(mono.astype(np.float32)**2)))

        for cb in self.on_sound_level:
            try:
                cb(rms)
            except Exception:
                pass

        # Echo suppression
        if speaker.is_speaking:
            if rms > self.interruption_threshold:
                print(f"\n[Interruption] RMS {rms:.1f} > {self.interruption_threshold}. Silencing Mani!")
                speaker.stop()
                self._set_state("LISTENING")
            return

        # Very short acoustic decay after speaker finishes (100ms)
        if (time.time() - speaker.last_spoke_time) < 0.10:
            return

        self.audio_queue.put((mono.copy(), rms))

    def _stream_processor(self, on_command_callback):
        """Main VAD worker that detects speech boundaries and triggers commands."""
        collected_frames = []
        speech_active = False
        speech_start_time = 0.0
        silence_start = None
        min_speech_frames = int(0.35 * self.sample_rate / self.blocksize)

        while not self._stop_requested:
            # Check conversation timeout
            if (self.in_conversation
                and not speaker.is_speaking
                and not self._processing
                and not speech_active
                and self.state == "CONVERSATION"):
                if time.time() > self.conversation_expiry:
                    self.end_conversation()

            try:
                block, rms = self.audio_queue.get(timeout=0.03)
            except queue.Empty:
                continue

            # Prevent concurrent phrase processing or capturing speaker echo
            if self._processing or speaker.is_speaking:
                speech_active = False
                silence_start = None
                collected_frames.clear()
                self.pre_buffer.append(block)
                continue

            if not speech_active:
                self.pre_buffer.append(block)

            current_silence_timeout = self.SILENCE_TIMEOUT_CONVO if self.in_conversation else self.SILENCE_TIMEOUT_STANDBY

            if rms > self.dynamic_threshold:
                if not speech_active:
                    speech_active = True
                    speech_start_time = time.time()
                    collected_frames = list(self.pre_buffer)
                    silence_start = None
                    if self.state not in ("PROCESSING", "SPEAKING"):
                        self._set_state("LISTENING")
                    if self.in_conversation:
                        self.conversation_expiry = time.time() + self.CONVERSATION_TIMEOUT
                collected_frames.append(block)
                silence_start = None
            elif speech_active:
                collected_frames.append(block)
                if silence_start is None:
                    silence_start = time.time()
                
                silence_elapsed = time.time() - silence_start
                speech_elapsed = time.time() - speech_start_time
                if (silence_elapsed > current_silence_timeout) or (speech_elapsed > self.max_speech_duration):
                    speech_active = False
                    silence_start = None
                    
                    if len(collected_frames) >= min_speech_frames:
                        raw_pcm = np.concatenate(collected_frames).astype(np.int16)
                        collected_frames = []
                        self._processing = True
                        
                        threading.Thread(
                            target=self._handle_completed_phrase,
                            args=(raw_pcm, on_command_callback),
                            daemon=True
                        ).start()
                    else:
                        collected_frames = []
                        if self.in_conversation:
                            self._set_state("CONVERSATION")
                        else:
                            self._set_state("STANDBY")

    def _handle_completed_phrase(self, pcm_int16: np.ndarray, on_command_callback):
        """Transcribes phrase and routes command."""
        self._processing = True
        try:
            self._set_state("PROCESSING")
            t0 = time.time()
            
            text = self.transcribe(pcm_int16)
            
            if not text:
                print(f"[Mic] No words detected. (audio {len(pcm_int16)/self.sample_rate:.1f}s, {(time.time()-t0)*1000:.0f}ms)")
                if self.in_conversation:
                    self.conversation_expiry = time.time() + self.CONVERSATION_TIMEOUT
                    self._set_state("CONVERSATION")
                else:
                    self._set_state("STANDBY")
                return

            total_ms = (time.time() - t0) * 1000
            print(f"\n[Heard]: \"{text}\" (total {total_ms:.0f}ms)")

            # === CONVERSATION MODE ===
            if self.in_conversation:
                self.conversation_expiry = time.time() + self.CONVERSATION_TIMEOUT
                
                is_wake, sub_cmd = self.check_wake_word(text)
                if is_wake and sub_cmd:
                    final_cmd = sub_cmd
                elif is_wake and not sub_cmd:
                    play_wake_chime()
                    self._set_state("LISTENING")
                    self.refresh_conversation()
                    return
                else:
                    final_cmd = text

                print(f"[Conversation] -> \"{final_cmd}\"")
                on_command_callback(final_cmd)
                return

            # === STANDBY MODE ===
            is_wake, command_suffix = self.check_wake_word(text)
            if is_wake:
                print(f"[{config.ASSISTANT_NAME} Wake!] \"{text}\"")
                play_wake_chime()

                for cb in self.on_wake_word_detected:
                    try:
                        cb(text)
                    except Exception:
                        pass

                self.start_conversation()

                if command_suffix:
                    print(f"[Standby -> Command] -> \"{command_suffix}\"")
                    on_command_callback(command_suffix)
                else:
                    self._set_state("LISTENING")
                    self.refresh_conversation()
                return

            # Check for direct actionable command even in STANDBY mode (e.g. "open youtube", "open browser", "take screenshot", "mute")
            from jarvis.brain.intent_router import intent_router
            is_action, _ = intent_router.check_direct_action(text)
            if is_action:
                print(f"[Standby Direct Action] -> \"{text}\"")
                play_wake_chime()
                self.start_conversation()
                on_command_callback(text)
            else:
                self._set_state("STANDBY")
        finally:
            self._processing = False

    def listen_and_transcribe_command(self, prompt_text: str | None = None) -> str:
        """Manual listen trigger from UI buttons."""
        if prompt_text:
            self._set_state("SPEAKING")
            speaker.speak(prompt_text, block=True)
            
        self._set_state("LISTENING")
        play_wake_chime()
        
        collected = []
        start_time = time.time()
        speech_started = False
        silence_start = None
        
        while (time.time() - start_time) < 8.0:
            try:
                block, rms = self.audio_queue.get(timeout=0.03)
                if rms > self.dynamic_threshold:
                    speech_started = True
                    collected.append(block)
                    silence_start = None
                elif speech_started:
                    collected.append(block)
                    if silence_start is None:
                        silence_start = time.time()
                    elif (time.time() - silence_start) > self.SILENCE_TIMEOUT_CONVO:
                        break
            except queue.Empty:
                continue
                
        if not collected:
            if self.in_conversation:
                self._set_state("CONVERSATION")
            else:
                self._set_state("STANDBY")
            return ""
            
        raw_pcm = np.concatenate(collected).astype(np.int16)
        self._set_state("PROCESSING")
        text = self.transcribe(raw_pcm)
        if self.in_conversation:
            self._set_state("CONVERSATION")
        else:
            self._set_state("STANDBY")
        return text

    def start_background_loop(self, on_command_callback):
        """Starts continuous hardware stream listening."""
        self._stop_requested = False
        self.calibrate_ambient_noise()
        
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                device=self.mic_index,
                blocksize=self.blocksize,
                callback=self._audio_callback
            )
            self.stream.start()
            stt_mode = "Vosk (instant offline)" if self._vosk_available else "Google Web (online)"
            print(f"[{config.ASSISTANT_NAME}] Audio stream active @ {self.sample_rate}Hz | STT: {stt_mode}")
        except Exception as e:
            print(f"[Stream Start Error] {e}")

        t = threading.Thread(target=self._stream_processor, args=(on_command_callback,), daemon=True)
        t.start()
        return t

    def stop(self):
        self._stop_requested = True
        self.in_conversation = False
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
        except Exception:
            pass
        self._set_state("STANDBY")

listener = JarvisListener()
