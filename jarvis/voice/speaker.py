import asyncio
import hashlib
import io
import threading
import time
from pathlib import Path
import edge_tts
import sounddevice as sd
import soundfile as sf
import numpy as np

from jarvis.config import config, CACHE_DIR

def is_malayalam_text(text: str) -> bool:
    """Returns True if the text contains Malayalam Unicode characters."""
    return any('\u0d00' <= char <= '\u0d7f' for char in text)


class JarvisSpeaker:
    def __init__(self):
        self.voice = config.VOICE
        self.rate = config.VOICE_RATE
        self.pitch = config.VOICE_PITCH
        self.is_speaking = False
        self.last_spoke_time = 0.0
        self._stop_requested = False
        self._lock = threading.Lock()
        self._current_stream = None
        
        # Callbacks for web HUD or listeners
        self.on_start_callbacks = []
        self.on_stop_callbacks = []
        self.on_audio_chunk_callbacks = []

        # Pre-warm frequent phrases (English & Malayalam)
        self.prewarm_cache()

    def get_target_voice(self, text: str) -> str:
        """Dynamically select Malayalam neural voice or English voice based on script and settings."""
        if is_malayalam_text(text) or config.AUDIO_LANGUAGE == "ml-IN":
            return config.MALAYALAM_VOICE
        return config.VOICE

    def prewarm_cache(self):
        """Pre-synthesizes common phrases in the background for instant <10ms playback."""
        phrases = [
            # English frequent phrases
            "Yes, sir?",
            "At your service.",
            "Online, sir.",
            "How can I help?",
            "How can I help you, sir?",
            "Right away, sir.",
            "Command executed.",
            "I'm right here, sir. Go ahead.",
            "Understood, sir. Standing by.",
            "You're very welcome, sir. Standing by.",
            "Good day, sir. Standing by whenever you need me.",
            f"Good day, sir. Systems initialized. {config.ASSISTANT_NAME} is online and at your service.",
            # Malayalam frequent phrases (മലയാളം)
            "ശരി, സാർ.",
            "തീർച്ചയായും സാർ.",
            "പറയൂ സാർ, ഞാൻ കേൾക്കുന്നുണ്ട്.",
            "സിസ്റ്റം പ്രവർത്തനസജ്ജമാണ്.",
            "നിങ്ങളുടെ സേവനത്തിനായി ഞാൻ ഇവിടെയുണ്ട്, സാർ.",
            "എന്താണ് ഞാൻ ചെയ്യേണ്ടത് സാർ?",
            "എല്ലാം തയ്യാറാണ് സാർ."
        ]
        def _worker():
            for p in phrases:
                try:
                    cpath = self._get_cache_path(p)
                    if not cpath.exists() or cpath.stat().st_size == 0:
                        asyncio.run(self._synthesize_to_file(p, cpath))
                except Exception:
                    pass
        threading.Thread(target=_worker, daemon=True).start()

    def register_callback(self, on_start=None, on_stop=None, on_chunk=None):
        if on_start:
            self.on_start_callbacks.append(on_start)
        if on_stop:
            self.on_stop_callbacks.append(on_stop)
        if on_chunk:
            self.on_audio_chunk_callbacks.append(on_chunk)

    def _get_cache_path(self, text: str) -> Path:
        """Hash text to cache frequent phrases (e.g. 'Yes, sir?' or 'ശരി, സാർ.')."""
        target_voice = self.get_target_voice(text)
        use_elevenlabs = bool(config.ELEVENLABS_API_KEY and not is_malayalam_text(text))
        engine = "elevenlabs" if use_elevenlabs else "edgetts"
        voice_tag = config.ELEVENLABS_VOICE_ID if use_elevenlabs else f"{target_voice}_{self.rate}_{self.pitch}"
        key = f"{text}_{engine}_{voice_tag}".encode("utf-8")
        hash_val = hashlib.md5(key).hexdigest()
        return CACHE_DIR / f"{hash_val}.mp3"

    def _synthesize_elevenlabs(self, text: str, output_path: Path) -> bool:
        """Synthesize speech using ElevenLabs REST API."""
        api_key = config.ELEVENLABS_API_KEY.strip()
        voice_id = config.ELEVENLABS_VOICE_ID.strip() or "pNInz6obpgDQGcFmaJgB"
        model_id = config.ELEVENLABS_MODEL_ID.strip() or "eleven_turbo_v2_5"

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        try:
            import requests
            res = requests.post(url, json=payload, headers=headers, timeout=12)
            if res.status_code == 200 and len(res.content) > 100:
                with open(output_path, "wb") as f:
                    f.write(res.content)
                return True
            else:
                print(f"[ElevenLabs API Notice] Status {res.status_code}: Falling back to Edge-TTS.")
        except Exception as e:
            print(f"[ElevenLabs Error] {e}. Falling back to Edge-TTS.")
        return False

    async def _synthesize_to_file(self, text: str, output_path: Path):
        target_voice = self.get_target_voice(text)

        # 1. Try ElevenLabs if configured (for non-Malayalam text)
        if config.ELEVENLABS_API_KEY and not is_malayalam_text(text):
            success = self._synthesize_elevenlabs(text, output_path)
            if success:
                return

        # 2. Edge-TTS with target voice (ml-IN-MidhunNeural for Malayalam, en-GB-RyanNeural for English)
        communicate = edge_tts.Communicate(
            text=text,
            voice=target_voice,
            rate=self.rate,
            pitch=self.pitch
        )
        await communicate.save(str(output_path))

    def _generate_audio_data(self, text: str) -> tuple[np.ndarray, int]:
        cache_path = self._get_cache_path(text)
        if not cache_path.exists() or cache_path.stat().st_size == 0:
            asyncio.run(self._synthesize_to_file(text, cache_path))
        data, samplerate = sf.read(str(cache_path))
        return data, samplerate


    def stop(self):
        """Immediately abort speech playback."""
        self._stop_requested = True
        try:
            sd.stop()
        except Exception:
            pass
        self.is_speaking = False
        for cb in self.on_stop_callbacks:
            try:
                cb()
            except Exception:
                pass

    def speak(self, text: str, block: bool = True):
        """Speak the given text using the neural voice."""
        if not text or not text.strip():
            return

        def _worker():
            with self._lock:
                self._stop_requested = False
                self.is_speaking = True
                
                # Notify start
                for cb in self.on_start_callbacks:
                    try:
                        cb(text)
                    except Exception:
                        pass
                
                try:
                    data, samplerate = self._generate_audio_data(text)
                    
                    # Play via sounddevice in chunks so visualizer gets live audio amplitude
                    chunk_size = int(samplerate * 0.05)  # 50ms chunks
                    total_samples = len(data)
                    channels = 1 if data.ndim == 1 else data.shape[1]
                    
                    try:
                        with sd.OutputStream(samplerate=samplerate, channels=channels, dtype='float32') as stream:
                            idx = 0
                            while idx < total_samples and not self._stop_requested:
                                end = min(idx + chunk_size, total_samples)
                                chunk = data[idx:end]
                                stream.write(chunk.astype(np.float32))
                                
                                # Calculate RMS amplitude for Arc Reactor pulsation
                                rms = float(np.sqrt(np.mean(chunk**2))) if len(chunk) > 0 else 0.0
                                for cb in self.on_audio_chunk_callbacks:
                                    try:
                                        cb(rms)
                                    except Exception:
                                        pass
                                
                                idx = end
                    except Exception as dev_err:
                        # Fallback to direct sd.play if stream creation fails
                        try:
                            sd.play(data, samplerate)
                            sd.wait()
                        except Exception:
                            # Final fallback: simulate RMS pulses for HUD
                            step = 0.05
                            dur = total_samples / samplerate
                            elapsed = 0
                            while elapsed < dur and not self._stop_requested:
                                time.sleep(step)
                                elapsed += step
                                for cb in self.on_audio_chunk_callbacks:
                                    try:
                                        cb(0.3)
                                    except Exception:
                                        pass
                except Exception as e:
                    print(f"[Speaker Error] {e}")
                finally:
                    self.is_speaking = False
                    self.last_spoke_time = time.time()
                    for cb in self.on_stop_callbacks:
                        try:
                            cb()
                        except Exception:
                            pass

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        if block:
            thread.join()

speaker = JarvisSpeaker()
