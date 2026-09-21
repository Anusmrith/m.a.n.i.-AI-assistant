import re
from jarvis.config import config
from jarvis.actions.system_control import system_controller
from jarvis.actions.telemetry import telemetry
from jarvis.actions.notes_manager import notes_manager
from jarvis.brain.llm_client import brain
from jarvis.voice.sfx import play_confirm_chime
from jarvis.voice.speaker import is_malayalam_text

MALAYALAM_APP_MAP = {
    "കാൽക്കുലേറ്റർ": "calc",
    "നോട്ട്പാഡ്": "notepad",
    "ക്രോം": "chrome",
    "ബ്രൗസർ": "chrome",
    "ഗൂഗിൾ ക്രോം": "chrome",
    "വാട്സ്ആപ്പ്": "whatsapp",
    "ടെർമിനൽ": "wt",
    "വിഎസ് കോഡ്": "code",
    "വിഷ്വൽ സ്റ്റുഡിയോ കോഡ്": "code",
    "കോഡ്": "code",
    "പെയിന്റ്": "mspaint",
    "ക്യാമറ": "camera",
    "സെറ്റിങ്സ്": "settings",
    "ഫയൽ എക്സ്പ്ലോറർ": "explorer",
    "ഫയലുകൾ": "explorer",
    "യൂട്യൂബ്": "youtube",
    "ഗൂഗിൾ": "google",
    "സ്പോട്ടിഫൈ": "spotify"
}


class IntentRouter:
    def clean_query(self, raw_query: str) -> str:
        """Cleans acoustic STT errors and normalizes conversational phrasing in English & Malayalam."""
        if not raw_query:
            return ""
        q = raw_query.lower().strip()

        # 1. Phonetic & acoustic corrections (English & Malayalam)
        q = re.sub(r'\byou\s*tube\b', 'youtube', q)
        q = re.sub(r'\bu\s*tube\b', 'youtube', q)
        q = re.sub(r'\butube\b', 'youtube', q)
        q = re.sub(r'\bto\s+tube\b', 'youtube', q)
        q = re.sub(r'\byour\s+tube\b', 'youtube', q)
        q = re.sub(r'\bbrowser\s+it\b', 'browser', q)
        q = re.sub(r'\bgoogle\s+chrome\b', 'chrome', q)
        q = re.sub(r'\bchrome\s+browser\b', 'chrome', q)
        q = re.sub(r'\bweb\s+browser\b', 'browser', q)
        q = re.sub(r'\bvs\s+code\b', 'vscode', q)
        q = re.sub(r'\bvisual\s+studio\s+code\b', 'vscode', q)

        # Malayalam acoustic normalization
        q = re.sub(r'\bയൂ\s*റ്റ്യൂബ്\b', 'യൂട്യൂബ്', q)
        q = re.sub(r'\bയൂ\s*ട്യൂബ്\b', 'യൂട്യൂബ്', q)
        q = re.sub(r'\bയുറ്റ്യൂബ്\b', 'യൂട്യൂബ്', q)

        # 2. Iteratively strip wake words, greetings, and leading conversational filler
        wake_terms = sorted([re.escape(w.lower()) for w in config.WAKE_WORDS], key=len, reverse=True)
        wake_pattern = "|".join(wake_terms)
        leading_pattern = (
            rf'^(?:{wake_pattern}|can you(?: please)?|could you(?: please)?|would you(?: please)?|'
            rf'will you(?: please)?|please|tell me|i want to|i want you to|i need to|i need you to|'
            rf'show me|give me|help me|go ahead and|just|open up|'
            rf'ദയവായി|ഒന്ന്|എനിക്ക്|പറഞ്ഞുതരാമോ|ചെയ്യാമോ|തുറക്കാമോ|പറയൂ|കാണിക്കാമോ)\s*[,:]?\s*'
        )

        prev = None
        while prev != q:
            prev = q
            q = re.sub(leading_pattern, '', q).strip()

        # 3. Strip trailing wake words and polite / filler words
        trailing_pattern = (
            rf'\s*[,:]?\s*(?:{wake_pattern}|please|for me|now|right now|quickly|if you can|website|site|page|app|application|'
            r'ദയവായി|വേഗം|ഒന്ന്|ചെയ്യ്|ചെയ്യുമോ)\s*$'
        )
        prev = None
        while prev != q:
            prev = q
            q = re.sub(trailing_pattern, '', q).strip()

        return q

    def check_direct_action(self, raw_query: str) -> tuple[bool, dict | None]:
        """
        Determines if a spoken query matches an explicit system, app, or website command.
        Used by the listener in STANDBY mode to obey direct commands without requiring the wake word.
        """
        cleaned = self.clean_query(raw_query)
        if not cleaned:
            return False, None

        # Check dismissal, volume, screenshot, lock, minimize, telemetry, time, date, weather, notes (English & Malayalam)
        direct_terms = [
            "system status", "battery", "cpu usage", "screenshot", "lock pc", "lock computer",
            "lock screen", "minimize", "show desktop", "mute", "unmute", "volume up", "volume down",
            "weather", "take a note", "read notes", "read my notes",
            "സിസ്റ്റം സ്റ്റാറ്റസ്", "ബാറ്ററി", "സ്ക്രീൻഷോട്ട്", "ലോക്ക്", "മിനിമൈസ്",
            "മ്യൂട്ട്", "അൺമ്യൂട്ട്", "ശബ്ദം", "സമയം", "തീയതി", "കാലാവസ്ഥ", "കുറിപ്പുകൾ"
        ]
        if any(term in cleaned for term in direct_terms):
            result = self.process(raw_query)
            return (True, result) if result.get("action") != "conversation" else (False, None)

        # Check YouTube or Browser
        if (
            "youtube" in cleaned or "browser" in cleaned or "chrome" in cleaned or
            cleaned in ["internet", "open internet"] or "യൂട്യൂബ്" in cleaned or
            "ബ്രൗസർ" in cleaned or "ക്രോം" in cleaned
        ):
            result = self.process(raw_query)
            return (True, result) if result.get("action") != "conversation" else (False, None)

        # Check app or website opening (English & Malayalam)
        if any(cleaned.startswith(p) for p in ["open ", "launch ", "start ", "run ", "play ", "go to ", "തുറക്കൂ ", "തുറക്കുക ", "തുറക്ക് ", "ഓപ്പൺ ചെയ്യ് "]):
            result = self.process(raw_query)
            return (True, result) if result.get("action") != "conversation" else (False, None)

        if any(cleaned.endswith(s) for s in [" തുറക്കൂ", " തുറക്കുക", " തുറക്ക്", " ഓപ്പൺ ചെയ്യ്", " ഓപ്പൺ ചെയ്യൂ"]):
            result = self.process(raw_query)
            return (True, result) if result.get("action") != "conversation" else (False, None)

        # Check clock / date triggers
        if any(w in cleaned for w in ["time", "clock", "date", "day today", "today's date", "സമയം", "തീയതി", "ഇന്ന്"]):
            result = self.process(raw_query)
            return (True, result) if result.get("action") != "conversation" else (False, None)

        return False, None

    def process(self, query: str, stream: bool = False) -> dict:
        """
        Processes user text or voice command.
        If stream=True, conversational questions return a generator without blocking.
        """
        raw_query = query.strip()
        q = self.clean_query(raw_query)
        is_ml = is_malayalam_text(raw_query) or is_malayalam_text(q)

        if not q:
            default_greeting = "എങ്ങനെ സഹായിക്കണം സാർ?" if is_ml else "How may I be of service, sir?"
            return {
                "query": raw_query,
                "response": default_greeting,
                "action": None,
                "data": None
            }

        # =========================================================================
        # 0. LANGUAGE SWITCHING INTENTS
        # =========================================================================
        ml_switch_terms = [
            "മലയാളത്തിൽ സംസാരിക്കൂ", "മലയാളം സംസാരിക്കുക", "മലയാളം പറയൂ",
            "മലയാളത്തിലേക്ക് മാറ്റൂ", "speak in malayalam", "switch to malayalam",
            "talk in malayalam", "change language to malayalam"
        ]
        if any(term in q for term in ml_switch_terms):
            play_confirm_chime()
            config.save_audio_language("ml-IN")
            reply = "തീർച്ചയായും സാർ, ഇനി മുതൽ ഞാൻ നിങ്ങളോട് മലയാളത്തിൽ സംസാരിക്കാം. എന്താണ് ഞാൻ ചെയ്യേണ്ടത്?"
            return {"query": raw_query, "response": reply, "action": "language", "data": {"language": "ml-IN"}}

        en_switch_terms = [
            "speak in english", "switch to english", "talk in english",
            "change language to english", "ഇംഗ്ലീഷിൽ സംസാരിക്കൂ", "ഇംഗ്ലീഷ് സംസാരിക്കുക"
        ]
        if any(term in q for term in en_switch_terms):
            play_confirm_chime()
            config.save_audio_language("en-IN")
            reply = "Switched to English, sir. Systems operational and standing by."
            return {"query": raw_query, "response": reply, "action": "language", "data": {"language": "en-IN"}}

        # =========================================================================
        # 1. DISMISSAL / FAREWELL / STANDBY
        # =========================================================================
        dismiss_terms = [
            "that's all", "thats all", "that is all", "that will be all", "that'll be all",
            "thank you", "thanks", "thank you so much", "thanks mani", "thank you mani",
            "bye", "goodbye", "bye bye", "see you", "see you later", "catch you later",
            "go to sleep", "sleep", "dismiss", "stand down", "standby", "stand by", "never mind",
            # Malayalam dismissals
            "മതി", "പോയി ഉറങ്ങൂ", "ഉറങ്ങിക്കോളൂ", "പോയ്ക്കോളൂ", "ബൈ", "ബൈ ബൈ", "വിട",
            "നന്ദി", "വളരെ നന്ദി", "നിൽക്കൂ", "സ്റ്റാൻഡ് ബൈ"
        ]
        if any(q == term for term in dismiss_terms) or any(q.startswith(term + " ") for term in ["thank you", "thanks", "that's all", "goodbye", "നന്ദി"]):
            if "thank" in q or "നന്ദി" in q:
                reply = "തീർച്ചയായും സാർ, സഹായിക്കാൻ കഴിഞ്ഞതിൽ സന്തോഷം. ഞാൻ ഇവിടെത്തന്നെയുണ്ട്." if is_ml else "You're very welcome, sir. Standing by."
            elif any(w in q for w in ["bye", "see you", "later", "ബൈ", "വിട"]):
                reply = "ശരി സാർ, ശുഭദിനം നേരുന്നു. എപ്പോൾ വേണമെങ്കിലും വിളിക്കാം." if is_ml else "Good day, sir. Standing by whenever you need me."
            else:
                reply = "ശരി സാർ, ഞാൻ സ്റ്റാൻഡ്ബൈയിൽ ഉണ്ടാകും." if is_ml else "Understood, sir. Standing by."
            return {
                "query": raw_query,
                "response": reply,
                "action": "standby",
                "data": None
            }

        # Stop / Silence / Cancel
        stop_terms = [
            "stop", "shut up", "be quiet", "cancel", "silent", "halt", "hush",
            "നിർത്തൂ", "സ്റ്റോപ്പ്", "മിണ്ടാതിരിക്ക്", "മിണ്ടാതിരിക്കൂ", "വാ അടയ്ക്കൂ", "നിർത്ത്", "നിർത്തുക"
        ]
        if any(term == q for term in stop_terms) or q.endswith(" stop") or q.startswith("stop ") or q.endswith(" നിർത്തൂ"):
            reply = "ശരി സാർ, നിർത്തുന്നു." if is_ml else "Understood, sir. Standing by."
            return {
                "query": raw_query,
                "response": reply,
                "action": "stop",
                "data": None
            }

        # =========================================================================
        # 2. SYSTEM TELEMETRY / DIAGNOSTICS
        # =========================================================================
        telemetry_terms = [
            "system status", "diagnostics", "battery", "cpu usage", "ram usage",
            "how is the system", "system diagnostic", "സിസ്റ്റം സ്റ്റാറ്റസ്",
            "സിസ്റ്റം പരിശോധിക്കൂ", "കമ്പ്യൂട്ടർ സ്റ്റാറ്റസ്", "സിപിയു", "റാം ഉപയോഗം"
        ]
        if any(term in q for term in telemetry_terms):
            play_confirm_chime()
            stats = telemetry.get_stats()
            if is_ml:
                cpu = stats.get("cpu_percent", 0)
                ram = stats.get("ram_percent", 0)
                bat = stats.get("battery_percent")
                bat_str = f"ബാറ്ററി {bat} ശതമാനം" if bat is not None else "ചാർജർ കണക്റ്റ് ചെയ്തിരിക്കുന്നു"
                reply = f"സിസ്റ്റം സ്റ്റാറ്റസ്: സിപിയു ഉപയോഗം {cpu} ശതമാനം, റാം ഉപയോഗം {ram} ശതമാനം, {bat_str} ആണ്, സാർ."
            else:
                reply = telemetry.get_voice_summary()
            return {
                "query": raw_query,
                "response": reply,
                "action": "telemetry",
                "data": stats
            }

        # =========================================================================
        # 3. SCREENSHOTS
        # =========================================================================
        screenshot_terms = ["screenshot", "capture screen", "സ്ക്രീൻഷോട്ട്", "സ്ക്രീൻ എടുക്ക്", "സ്ക്രീൻ സേവ് ചെയ്യ്", "സ്ക്രീൻഷോട്ട് എടുക്കൂ"]
        if any(term in q for term in screenshot_terms):
            play_confirm_chime()
            filepath, en_reply = system_controller.take_screenshot()
            reply = "സ്ക്രീൻഷോട്ട് വിജയകരമായി സേവ് ചെയ്തു, സാർ." if is_ml else en_reply
            return {
                "query": raw_query,
                "response": reply,
                "action": "screenshot",
                "data": {"filepath": filepath}
            }

        # =========================================================================
        # 4. LOCK WORKSTATION
        # =========================================================================
        lock_terms = ["lock pc", "lock computer", "lock screen", "lock workstation", "ലോക്ക് ചെയ്യ്", "ലോക്ക് ചെയ്യൂ", "കമ്പ്യൂട്ടർ ലോക്ക് ചെയ്യ്", "സ്ക്രീൻ ലോക്ക് ചെയ്യ്"]
        if any(term in q for term in lock_terms):
            play_confirm_chime()
            system_controller.lock_workstation()
            reply = "സുരക്ഷാ പ്രോട്ടോക്കോൾ സജീവമാക്കി. കമ്പ്യൂട്ടർ ലോക്ക് ചെയ്തു, സാർ." if is_ml else "Security protocols engaged. Workstation locked, sir."
            return {
                "query": raw_query,
                "response": reply,
                "action": "lock",
                "data": None
            }

        # =========================================================================
        # 5. MINIMIZE WINDOWS / SHOW DESKTOP
        # =========================================================================
        minimize_terms = ["minimize", "show desktop", "clear screen", "minimize windows", "minimize all", "മിനിമൈസ് ചെയ്യ്", "മിനിമൈസ് ചെയ്യൂ", "ഡെസ്ക്ടോപ്പ് കാണിക്ക്"]
        if any(term in q for term in minimize_terms):
            play_confirm_chime()
            system_controller.minimize_windows()
            reply = "എല്ലാ വിൻഡോകളും മിനിമൈസ് ചെയ്തു, സാർ." if is_ml else "Desktop cleared, all windows minimized, sir."
            return {
                "query": raw_query,
                "response": reply,
                "action": "minimize",
                "data": None
            }

        # =========================================================================
        # 6. VOLUME CONTROLS
        # =========================================================================
        if any(term in q for term in ["mute", "മ്യൂട്ട് ചെയ്യൂ", "മ്യൂട്ട്", "ശബ്ദം നിശബ്ദമാക്കൂ", "ശബ്ദം ഓഫ് ചെയ്യ്"]) and "unmute" not in q and "അൺമ്യൂട്ട്" not in q:
            play_confirm_chime()
            system_controller.control_volume("mute")
            reply = "ശബ്ദം നിശബ്ദമാക്കി, സാർ." if is_ml else "Audio output muted, sir."
            return {"query": raw_query, "response": reply, "action": "volume", "data": {"type": "mute"}}

        if any(term in q for term in ["unmute", "അൺമ്യൂട്ട് ചെയ്യൂ", "അൺമ്യൂട്ട്", "ശബ്ദം ഓണാക്കൂ", "ശബ്ദം തരൂ"]):
            play_confirm_chime()
            system_controller.control_volume("unmute")
            reply = "ശബ്ദം പുനഃസ്ഥാപിച്ചു, സാർ." if is_ml else "Audio output unmuted, sir."
            return {"query": raw_query, "response": reply, "action": "volume", "data": {"type": "unmute"}}

        vol_match = re.search(r'set volume to (\d+)', q)
        if vol_match:
            play_confirm_chime()
            level = int(vol_match.group(1))
            reply = system_controller.control_volume("set", level)
            return {"query": raw_query, "response": reply, "action": "volume", "data": {"level": level}}

        if any(term in q for term in ["volume up", "increase volume", "raise volume", "louder", "ശബ്ദം കൂട്ടൂ", "ശബ്ദം കൂട്ടുക", "ശബ്ദം ഉയർത്തൂ", "ശബ്ദം കൂട്ടണം"]):
            play_confirm_chime()
            system_controller.control_volume("up")
            reply = "ശബ്ദം കൂട്ടിയിട്ടുണ്ട്, സാർ." if is_ml else "Master volume increased."
            return {"query": raw_query, "response": reply, "action": "volume", "data": {"type": "up"}}

        if any(term in q for term in ["volume down", "decrease volume", "lower volume", "quieter", "ശബ്ദം കുറയ്ക്കൂ", "ശബ്ദം കുറയ്ക്കുക", "ശബ്ദം താഴ്ത്തൂ", "ശബ്ദം കുറയ്ക്കണം"]):
            play_confirm_chime()
            system_controller.control_volume("down")
            reply = "ശബ്ദം കുറച്ചിട്ടുണ്ട്, സാർ." if is_ml else "Master volume decreased."
            return {"query": raw_query, "response": reply, "action": "volume", "data": {"type": "down"}}

        # =========================================================================
        # 7. MEDIA CONTROLS
        # =========================================================================
        if any(term in q for term in ["play music", "pause music", "pause song", "resume music", "പാട്ട് പ്ലേ ചെയ്യ്", "പാട്ട് നിർത്തൂ"]) or q in ["play", "pause", "പ്ലേ", "പോസ്"]:
            play_confirm_chime()
            reply = system_controller.control_media("playpause")
            return {"query": raw_query, "response": reply, "action": "media", "data": {"action": "playpause"}}

        if any(term in q for term in ["next song", "next track", "skip song", "skip track", "അടുത്ത പാട്ട്"]):
            play_confirm_chime()
            reply = system_controller.control_media("next")
            return {"query": raw_query, "response": reply, "action": "media", "data": {"action": "next"}}

        if any(term in q for term in ["previous song", "previous track", "back track", "മുമ്പത്തെ പാട്ട്"]):
            play_confirm_chime()
            reply = system_controller.control_media("previous")
            return {"query": raw_query, "response": reply, "action": "media", "data": {"action": "prev"}}

        # =========================================================================
        # 8. TIME & CLOCK
        # =========================================================================
        time_triggers_en = [
            "what time", "whats the time", "what's the time", "what is the time",
            "tell me the time", "tell me time", "current time", "the time",
            "time right now", "time now", "time please", "clock", "check time"
        ]
        time_triggers_ml = [
            "സമയം എത്രയായി", "ഇപ്പോഴത്തെ സമയം", "സമയം പറ", "സമയം എന്താണ്",
            "സമയം പറ മാണി", "സമയം എത്ര", "ക്ലോക്ക്"
        ]
        if (
            any(term in q for term in time_triggers_en) or any(term in q for term in time_triggers_ml) or
            q in ["time", "the time", "current time", "what time is it", "സമയം", "ക്ലോക്ക്"]
        ) and not any(w in q for w in ["first time", "how much time", "take time", "time machine", "time travel", "timeline"]):
            play_confirm_chime()
            reply = system_controller.get_time_malayalam() if is_ml else system_controller.get_time()
            return {"query": raw_query, "response": reply, "action": "time", "data": None}

        # =========================================================================
        # 9. DATE & DAY
        # =========================================================================
        date_triggers_en = [
            "what date", "whats the date", "what's the date", "what is the date",
            "what day", "whats the day", "what's the day", "what is the day",
            "today's date", "todays date", "date today", "day today", "current date",
            "tell me the date", "what is today's date", "what day is it", "what day is today"
        ]
        date_triggers_ml = [
            "ഇന്നത്തെ തീയതി", "തീയതി എത്രയാണ്", "ഇന്ന് ഏത് ദിവസമാണ്", "തീയതി പറ",
            "ഇന്ന് എന്ത് ദിവസം", "ഇന്നത്തെ ദിവസം"
        ]
        if (
            any(term in q for term in date_triggers_en) or any(term in q for term in date_triggers_ml) or
            q in ["date", "the date", "what day is it", "day today", "തീയതി", "ഇന്ന്"]
        ) and not any(w in q for w in ["blind date", "date night", "expiry date", "release date"]):
            play_confirm_chime()
            reply = system_controller.get_date_malayalam() if is_ml else system_controller.get_date()
            return {"query": raw_query, "response": reply, "action": "date", "data": None}

        # =========================================================================
        # 10. WEATHER
        # =========================================================================
        if "weather" in q or "കാലാവസ്ഥ" in q:
            play_confirm_chime()
            city_match = re.search(r'weather (?:in|for|at)\s+([a-zA-Z\s]+)', q)
            city = city_match.group(1).strip() if city_match else None
            reply = system_controller.get_weather(city)
            return {"query": raw_query, "response": reply, "action": "weather", "data": {"city": city}}

        # =========================================================================
        # 11. NOTES MANAGEMENT
        # =========================================================================
        note_add_match = (
            re.search(r'^(?:take a note|write a note|take note|save note|add note)\s*[:]?\s*(.+)$', q) or
            re.search(r'^(?:കുറിപ്പ് എടുക്കൂ|നോട്ട് എടുക്കൂ|സേവ് ചെയ്യ്)\s*[:]?\s*(.+)$', q)
        )
        if note_add_match:
            play_confirm_chime()
            content = note_add_match.group(1)
            note = notes_manager.add_note(content)
            reply = f"കുറിപ്പ് രേഖപ്പെടുത്തി: '{content}', സാർ." if is_ml else f"Note recorded to database: '{content}', sir."
            return {"query": raw_query, "response": reply, "action": "note_add", "data": note}

        if any(term in q for term in ["read my notes", "read notes", "show my notes", "list notes", "കുറിപ്പുകൾ വായിക്കൂ", "എന്റെ കുറിപ്പുകൾ"]):
            play_confirm_chime()
            reply = notes_manager.get_voice_summary()
            return {"query": raw_query, "response": reply, "action": "note_list", "data": notes_manager.list_notes()}

        if any(term in q for term in ["clear notes", "delete notes", "clear all notes", "കുറിപ്പുകൾ മായ്ക്കൂ"]):
            play_confirm_chime()
            count = notes_manager.clear_notes()
            reply = f"ശരി സാർ. {count} കുറിപ്പുകൾ മായ്ച്ചു കളഞ്ഞു." if is_ml else f"Acknowledged, sir. Purged {count} notes from the database."
            return {"query": raw_query, "response": reply, "action": "note_clear", "data": {"deleted": count}}

        # =========================================================================
        # 12. COMPREHENSIVE YOUTUBE INTENTS (English & Malayalam)
        # =========================================================================
        # Malayalam YouTube search patterns:
        # e.g. "യൂട്യൂബിൽ [പാട്ട്] പ്ലേ ചെയ്യ്", "[query] യൂട്യൂബിൽ പ്ലേ ചെയ്യ്", "യൂട്യൂബിൽ [query] കാണിക്കൂ"
        ml_yt_match = (
            re.search(r'^യൂട്യൂബിൽ\s+(.+?)\s+(?:പ്ലേ ചെയ്യ്|പ്ലേ ചെയ്യൂ|തിരയൂ|സെർച്ച് ചെയ്യ്|കാണിക്കൂ|വെക്കൂ)$', q) or
            re.search(r'^(.+?)\s+യൂട്യൂബിൽ\s+(?:പ്ലേ ചെയ്യ്|പ്ലേ ചെയ്യൂ|തിരയൂ|സെർച്ച് ചെയ്യ്|കാണിക്കൂ|വെക്കൂ)$', q) or
            re.search(r'^യൂട്യൂബിൽ\s+(.+)$', q)
        )
        if ml_yt_match:
            term = ml_yt_match.group(1).strip()
            if not term or term in ["തുറക്കൂ", "തുറക്കുക", "ഓപ്പൺ ചെയ്യ്", "പോവുക"]:
                play_confirm_chime()
                system_controller.open_website("youtube")
                return {"query": raw_query, "response": "തീർച്ചയായും സാർ, യൂട്യൂബ് തുറക്കുന്നു.", "action": "website", "data": {"site": "youtube"}}
            play_confirm_chime()
            system_controller.youtube_search(term)
            return {"query": raw_query, "response": f"യൂട്യൂബിൽ '{term}' പ്ലേ ചെയ്യുന്നു, സാർ.", "action": "youtube", "data": {"term": term}}

        # English YouTube search
        yt_search_match = (
            re.search(r'^(?:play|search for|search|find)\s+(.+?)\s+on youtube$', q) or
            re.search(r'^youtube\s+(?:search for|search|find|play)\s+(.+)$', q) or
            re.search(r'^search youtube for\s+(.+)$', q)
        )
        if yt_search_match:
            term = yt_search_match.group(1).strip()
            if not term or term in ["youtube", "video", "videos"]:
                play_confirm_chime()
                reply = system_controller.open_website("youtube")
                return {"query": raw_query, "response": reply, "action": "website", "data": {"site": "youtube"}}
            play_confirm_chime()
            reply = system_controller.youtube_search(term)
            return {"query": raw_query, "response": reply, "action": "youtube", "data": {"term": term}}

        if "youtube" in q or "യൂട്യൂബ്" in q:
            extra_search = re.search(r'youtube\s+(?:and search for|search for|search|and play|play)\s+(.+)$', q)
            if extra_search:
                term = extra_search.group(1).strip()
                play_confirm_chime()
                reply = system_controller.youtube_search(term)
                return {"query": raw_query, "response": reply, "action": "youtube", "data": {"term": term}}

            play_confirm_chime()
            system_controller.open_website("youtube")
            reply = "തീർച്ചയായും സാർ, യൂട്യൂബ് തുറക്കുന്നു." if is_ml else "Accessing Youtube, sir."
            return {"query": raw_query, "response": reply, "action": "website", "data": {"site": "youtube"}}

        # =========================================================================
        # 13. COMPREHENSIVE BROWSER / CHROME INTENTS (English & Malayalam)
        # =========================================================================
        browser_terms = [
            "browser", "open browser", "launch browser", "start browser",
            "open the browser", "the browser", "web browser", "open web browser",
            "internet", "open internet", "chrome", "open chrome", "launch chrome",
            "start chrome", "google chrome", "open google chrome", "my browser",
            "open my browser", "ബ്രൗസർ തുറക്കൂ", "ക്രോം തുറക്കൂ", "നെറ്റ് തുറക്കൂ", "ഗൂഗിൾ തുറക്കൂ"
        ]
        if q in browser_terms or any(q.startswith(p) for p in ["open browser", "launch browser", "open chrome", "launch chrome"]):
            play_confirm_chime()
            success, _ = system_controller.launch_app("chrome")
            if not success:
                success, _ = system_controller.launch_app("edge")
            if not success:
                system_controller.open_website("google")
            reply = "ബ്രൗസർ തുറക്കുന്നു, സാർ." if is_ml else "Accessing Chrome, sir."
            return {"query": raw_query, "response": reply, "action": "launch", "data": {"app": "browser", "success": True}}

        # Common websites direct summon
        direct_sites = {
            "google": "google",
            "github": "github",
            "reddit": "reddit",
            "netflix": "netflix",
            "gmail": "gmail",
            "twitter": "twitter",
            "x": "x",
            "chatgpt": "chatgpt",
            "spotify": "spotify",
        }
        for site, target in direct_sites.items():
            if q == site or q == f"open {site}" or q == f"launch {site}" or q == f"go to {site}" or q == f"visit {site}":
                play_confirm_chime()
                reply = system_controller.open_website(target)
                return {"query": raw_query, "response": reply, "action": "website", "data": {"site": site}}

        # 14. Google Web Search
        search_match = re.search(r'^(?:search for|google|search google for)\s+(.+)$', q)
        if search_match:
            play_confirm_chime()
            query_term = search_match.group(1).strip()
            reply = system_controller.web_search(query_term)
            return {"query": raw_query, "response": reply, "action": "search", "data": {"term": query_term}}

        # =========================================================================
        # 15. GENERAL APP OR WEBSITE LAUNCH (English & Malayalam)
        # =========================================================================
        # Check Malayalam app open patterns: e.g. "കാൽക്കുലേറ്റർ തുറക്കൂ", "നോട്ട്പാഡ് ഓപ്പൺ ചെയ്യ്"
        ml_open_match = (
            re.search(r'^(.+?)\s+(?:തുറക്കൂ|തുറക്കുക|തുറക്ക്|ഓപ്പൺ ചെയ്യ്|ഓപ്പൺ ചെയ്യൂ)$', q) or
            re.search(r'^(?:തുറക്കൂ|തുറക്കുക|തുറക്ക്|ഓപ്പൺ ചെയ്യ്)\s+(.+)$', q)
        )
        if ml_open_match:
            app_word = ml_open_match.group(1).strip()
            target_app = MALAYALAM_APP_MAP.get(app_word, app_word)
            play_confirm_chime()
            if target_app in direct_sites:
                system_controller.open_website(direct_sites[target_app])
                reply = f"{app_word.title()} തുറക്കുന്നു, സാർ."
                return {"query": raw_query, "response": reply, "action": "website", "data": {"site": target_app}}
            else:
                success, _ = system_controller.launch_app(target_app)
                reply = f"{app_word} തുറക്കുന്നു, സാർ." if success else f"{app_word} തുറക്കാൻ സാധിച്ചില്ല, സാർ."
                return {"query": raw_query, "response": reply, "action": "launch", "data": {"app": target_app, "success": success}}

        # English app launch
        launch_match = re.search(r'^(?:open|launch|start|run|access|visit)\s+(.+)$', q)
        if launch_match:
            app_target = launch_match.group(1).strip()
            app_target = re.sub(r'^(?:the|a|an)\s+', '', app_target).strip()
            app_target = re.sub(r'\s+(?:website|site|page|app|application|program)$', '', app_target).strip()

            if app_target in ["browser", "web browser", "internet", "my browser", "chrome"]:
                play_confirm_chime()
                success, reply = system_controller.launch_app("chrome")
                if not success:
                    reply = system_controller.open_website("google")
                return {"query": raw_query, "response": reply, "action": "launch", "data": {"app": "browser"}}

            if app_target in direct_sites:
                play_confirm_chime()
                reply = system_controller.open_website(direct_sites[app_target])
                return {"query": raw_query, "response": reply, "action": "website", "data": {"site": app_target}}

            play_confirm_chime()
            success, reply = system_controller.launch_app(app_target)
            return {"query": raw_query, "response": reply, "action": "launch", "data": {"app": app_target, "success": success}}

        # =========================================================================
        # 16. CONVERSATIONAL / LLM GENERAL INTELLIGENCE (Gemini / Offline)
        # =========================================================================
        quick_reply = brain.quick_offline_match(q) or brain.quick_offline_match(raw_query)
        if quick_reply:
            return {
                "stream": False,
                "query": raw_query,
                "response": quick_reply,
                "action": "conversation",
                "data": None
            }

        if stream:
            return {
                "stream": True,
                "query": raw_query,
                "generator": brain.stream_ask(q or raw_query),
                "action": "conversation",
                "data": None
            }

        reply = brain.ask(q or raw_query)
        return {
            "stream": False,
            "query": raw_query,
            "response": reply,
            "action": "conversation",
            "data": None
        }

    def process_stream(self, query: str) -> dict:
        """
        Processes command and returns streaming generator for conversational questions,
        or instant response dict for local actions and quick replies with zero redundant calls.
        """
        return self.process(query, stream=True)


intent_router = IntentRouter()

