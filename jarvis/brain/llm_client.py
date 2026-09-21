import os
import re
import math
import random
import urllib.parse
import requests

from jarvis.config import config

class JarvisBrain:
    GEMINI_MODELS = [
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
    ]


    def __init__(self):
        self.gemini_client = None
        self.active_model = self.GEMINI_MODELS[0]
        self._init_gemini()

    def _init_gemini(self):
        api_key = config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if api_key and api_key.strip():
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(
                    api_key=api_key.strip(),
                    http_options=types.HttpOptions(timeout=10000)
                )
                for model_name in self.GEMINI_MODELS:
                    try:
                        res = client.models.generate_content(
                            model=model_name,
                            contents="ping",
                            config={"max_output_tokens": 5}
                        )
                        if res and res.text:
                            self.gemini_client = client
                            self.active_model = model_name
                            print(f"[Brain] Google Gemini connected successfully using {model_name}.")
                            return
                    except Exception:
                        continue
                self.gemini_client = client
            except Exception as e:
                self.gemini_client = None
                print(f"[Brain] Could not initialize Gemini: {e}")

    def set_gemini_api_key(self, api_key: str) -> tuple[bool, str]:
        """Validates and saves a new Gemini API key with fast 1-second verification."""
        clean_key = api_key.strip()
        if not clean_key:
            return False, "API key cannot be empty."

        try:
            from google import genai
            from google.genai import types
            test_client = genai.Client(
                api_key=clean_key,
                http_options=types.HttpOptions(timeout=15000)
            )
            
            # Prioritize testing with the fast active model first
            test_models = [self.active_model] + [m for m in self.GEMINI_MODELS if m != self.active_model]
            last_err = None
            for model_name in test_models[:2]:
                try:
                    test_resp = test_client.models.generate_content(
                        model=model_name,
                        contents="Respond with the single word 'READY'",
                        config=types.GenerateContentConfig(
                            max_output_tokens=10,
                            temperature=0.0
                        )
                    )
                    if test_resp and test_resp.text:
                        self.gemini_client = test_client
                        self.active_model = model_name
                        config.save_gemini_api_key(clean_key)
                        print(f"[Brain] Gemini API key verified and saved successfully with {model_name}!")
                        return True, f"Connected to Gemini AI! (Model: {model_name})"
                except Exception as err:
                    last_err = err
                    continue

            return False, f"Verification failed: {last_err}"
        except Exception as e:
            err_msg = str(e)
            print(f"[Brain] Gemini verification failed: {err_msg}")
            return False, f"Verification failed: {err_msg}"

    def is_gemini_connected(self) -> bool:
        """Returns True if Gemini client is initialized."""
        return self.gemini_client is not None

    def _get_system_prompt(self) -> str:
        """Returns the current system prompt tuned for crisp, spoken voice assistant replies."""
        import datetime
        now_ctx = datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        return (
            f"{config.SYSTEM_PROMPT}\n"
            f"Current local computer time: {now_ctx}.\n"
            "CRITICAL SPOKEN VOICE RULES:\n"
            "- You are speaking aloud directly to the user.\n"
            "- Keep answers concise, natural, and conversational in 1 to 2 crisp sentences (under 35 words), "
            "unless the user specifically asks for detail, steps, or explanation.\n"
            "- Never output markdown symbols, asterisks (*), hashtags (#), or bullet points."
        )

    def query_llm(self, prompt: str) -> str | None:
        """Attempt to query Gemini with fast timeout protection and offline fallback."""
        sys_prompt = self._get_system_prompt()

        # 1. Try Gemini (Primary Cloud LLM)
        if self.gemini_client:
            try:
                from google.genai import types
                response = self.gemini_client.models.generate_content(
                    model=self.active_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_prompt,
                        temperature=0.7,
                        max_output_tokens=85
                    )
                )
                if response and response.text:
                    clean_text = re.sub(r'[*_#`]', '', response.text).strip()
                    return clean_text
            except Exception as e:
                # Try fallback fast model to prevent timeout cascading
                alt_model = "gemini-3.5-flash-lite" if self.active_model != "gemini-3.5-flash-lite" else "gemini-3.1-flash-lite"
                try:
                    from google.genai import types
                    response = self.gemini_client.models.generate_content(
                        model=alt_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=sys_prompt,
                            temperature=0.7,
                            max_output_tokens=85
                        )
                    )
                    if response and response.text:
                        self.active_model = alt_model
                        clean_text = re.sub(r'[*_#`]', '', response.text).strip()
                        return clean_text
                except Exception:
                    pass
                print(f"[Gemini API Notice] {e}. Using offline intelligent response.")

        # 2. Try Ollama ONLY IF explicitly enabled in configuration
        if config.OLLAMA_ENABLED:
            try:
                res = requests.post(
                    f"{config.OLLAMA_URL}/api/generate",
                    json={
                        "model": config.OLLAMA_MODEL,
                        "prompt": prompt,
                        "system": config.SYSTEM_PROMPT,
                        "stream": False
                    },
                    timeout=1.5
                )
                if res.status_code == 200:
                    return res.json().get("response", "").strip()
            except Exception:
                pass

        # Zero-delay drop to offline respond
        return None

    def stream_query_llm(self, prompt: str):
        """
        Ultra-low-latency streaming LLM generator.
        Yields complete sentences as soon as sentence-ending punctuation is encountered,
        allowing the speaker to start synthesizing and playing audio while subsequent sentences are generated.
        """
        sys_prompt = self._get_system_prompt()

        if self.gemini_client:
            try:
                from google.genai import types
                stream = self.gemini_client.models.generate_content_stream(
                    model=self.active_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=sys_prompt,
                        temperature=0.7,
                        max_output_tokens=85
                    )
                )
                accumulated = ""
                for chunk in stream:
                    if not chunk.text:
                        continue
                    accumulated += chunk.text
                    # Check for sentence boundaries: [.!?] followed by whitespace or end of token
                    while True:
                        m = re.search(r'([.!?]+(?:\s+|\Z)|\n+)', accumulated)
                        if not m:
                            break
                        end_idx = m.end()
                        sentence = accumulated[:end_idx].strip()
                        accumulated = accumulated[end_idx:]
                        if sentence:
                            clean_sentence = re.sub(r'[*_#`]', '', sentence).strip()
                            if clean_sentence:
                                yield clean_sentence

                remaining = accumulated.strip()
                if remaining:
                    clean_remaining = re.sub(r'[*_#`]', '', remaining).strip()
                    if clean_remaining:
                        yield clean_remaining
                return
            except Exception as e:
                print(f"[Gemini Stream Notice] {e}. Falling back to standard query.")

        # Fallback if streaming failed or Gemini unavailable
        fallback_ans = self.query_llm(prompt) or self.offline_respond(prompt)
        if fallback_ans:
            sentences = re.split(r'(?<=[.!?])\s+', fallback_ans)
            for s in sentences:
                s_clean = s.strip()
                if s_clean:
                    yield s_clean



    def query_wikipedia(self, topic: str) -> str | None:
        """Fetch concise encyclopedic summary from Wikipedia."""
        try:
            clean = urllib.parse.quote(topic.strip())
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean}"
            headers = {"User-Agent": "JarvisPersonalAssistant/1.0"}
            res = requests.get(url, headers=headers, timeout=4)
            if res.status_code == 200:
                data = res.json()
                extract = data.get("extract")
                if extract:
                    # Keep to 1-2 sentences
                    sentences = extract.split(". ")
                    short_summary = ". ".join(sentences[:2])
                    if not short_summary.endswith("."):
                        short_summary += "."
                    return f"According to historical records, {short_summary}"
        except Exception:
            pass
        return None

    def calculate_math(self, expression: str) -> str | None:
        """Safely compute mathematical calculations."""
        clean = expression.lower()
        clean = re.sub(r'^(what is|calculate|solve|evaluate)\s+', '', clean)
        clean = clean.replace('plus', '+').replace('minus', '-').replace('times', '*').replace('multiplied by', '*').replace('divided by', '/').replace('x', '*').replace('^', '**')
        clean = re.sub(r'[^0-9+\-*/().% ]', '', clean).strip()
        
        if not clean:
            return None
            
        try:
            # Safe evaluation with restricted globals
            safe_dict = {"__builtins__": None, "math": math}
            result = eval(clean, safe_dict)
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            return f"The calculated result is {result}, sir."
        except Exception:
            return None

    def offline_respond(self, query: str) -> str:
        """High-fidelity offline heuristic fallback for conversational queries in English & Malayalam."""
        q = query.lower().strip()

        # Math detection
        if any(w in q for w in ["calculate", "multiply", "plus", "minus", "divided by", "times", "multiplied by", "into", " + ", " - ", " * ", " / "]) or re.match(r'^[\d\s+\-*/()^.]+$', q):
            math_ans = self.calculate_math(q)
            if math_ans:
                return math_ans

        # Wikipedia / definition detection ("who is...", "what is...", "tell me about...")
        wiki_match = re.search(r'^(who is|what is|tell me about|who was)\s+(.+)$', q)
        if wiki_match:
            subject = wiki_match.group(2).strip(" ?.")
            if not any(x in subject for x in ["your name", "time", "date", "weather", "battery", "cpu", "ram"]):
                wiki_summary = self.query_wikipedia(subject)
                if wiki_summary:
                    return wiki_summary

        # Persona & Dialogue checks - Malayalam & English
        if any(g in q for g in ["കേൾക്കാമോ", "കേൾക്കുന്നുണ്ടോ", "ശബ്ദം കേൾക്കുന്നുണ്ടോ", "can you hear me", "are you listening", "am i audible", "hear me"]):
            if any('\u0d00' <= c <= '\u0d7f' for c in q):
                return "തീർച്ചയായും സാർ! ഞാൻ വ്യക്തമായി കേൾക്കുന്നുണ്ട്. എല്ലാ ഓഡിയോ സെൻസറുകളും പൂർണ്ണമായി പ്രവർത്തനക്ഷമമാണ്."
            return "Yes, sir! I hear you loud and clear. All acoustic sensors are fully operational."

        if any(g in q for g in ["അവിടെ ഉണ്ടോ", "ഇവിടെ ഉണ്ടോ", "are you there", "you there"]):
            if any('\u0d00' <= c <= '\u0d7f' for c in q):
                return "ഞാൻ ഇവിടെത്തന്നെയുണ്ട് സാർ. നിങ്ങളുടെ നിർദ്ദേശങ്ങൾക്കായി കാത്തിരിക്കുന്നു."
            return "Always right here, sir. Standing by for your instructions."

        if any(g == q for g in ["നമസ്കാരം", "ഹലോ", "ഹായ്", "സുപ്രഭാതം", "hello", "hi", "hey", "good morning", "good evening", "good afternoon"]):
            if any('\u0d00' <= c <= '\u0d7f' for c in q):
                return "നമസ്കാരം സാർ! ഞാൻ മാണി. ഞാൻ എങ്ങനെ സഹായിക്കണം?"
            return "Hello, sir! How may I assist you today?"

        if any(g in q for g in ["നീ ആരാണ്", "ആരാണ് നീ", "നിങ്ങൾ ആരാണ്", "ആരാണ് നിങ്ങൾ", "who are you", "what are you", "introduce yourself"]):
            if any('\u0d00' <= c <= '\u0d7f' for c in q):
                return (
                    f"ഞാൻ {config.ASSISTANT_NAME}, നിങ്ങളുടെ കമ്പ്യൂട്ടർ നിയന്ത്രിക്കാനും വിവരങ്ങൾ നൽകാനും രൂപകൽപ്പന ചെയ്ത "
                    "പേഴ്സണൽ ആർട്ടിഫിഷ്യൽ ഇന്റലിജൻസ് അസിസ്റ്റന്റ് ആണ്. നിങ്ങളുടെ സേവനത്തിനായി ഞാൻ എപ്പോഴും സജ്ജനാണ്, സാർ."
                )
            return (
                f"I am {config.ASSISTANT_NAME}, an advanced personal artificial intelligence system designed to manage your computer, "
                "automate your tasks, and assist you in any endeavor. At your service, sir."
            )
            
        if any(g in q for g in ["ആരാണ് ഉണ്ടാക്കിയത്", "who made you", "who created you"]):
            if any('\u0d00' <= c <= '\u0d7f' for c in q):
                return f"ഞാൻ {config.ASSISTANT_NAME}, നിങ്ങളുടെ ഡെസ്ക്ടോപ്പ് സഹായിയായി രൂപകൽപ്പന ചെയ്യപ്പെട്ടതാണ്, സാർ."
            return f"I am {config.ASSISTANT_NAME}, tailored right here to be your dedicated desktop companion."

        if any(g in q for g in ["സുഖമാണോ", "എങ്ങനെ ഇരിക്കുന്നു", "വിശേഷം എന്താണ്", "how are you", "how's it going", "status"]):
            if any('\u0d00' <= c <= '\u0d7f' for c in q):
                return "എനിക്ക് സുഖമാണ് സാർ, എല്ലാ സിസ്റ്റങ്ങളും പൂർണ്ണ ശേഷിയിൽ പ്രവർത്തിക്കുന്നു. എന്താണ് ഞാൻ ചെയ്യേണ്ടത്?"
            return "Operating at peak computational efficiency, sir. All subsystems are optimal and ready for your command."

        if any(g in q for g in ["നന്ദി", "വളരെ നന്ദി", "താങ്ക് യു", "thank you", "thanks", "good job", "well done"]):
            if any('\u0d00' <= c <= '\u0d7f' for c in q):
                return "സഹായിക്കാൻ കഴിഞ്ഞതിൽ സന്തോഷം സാർ, ഞാൻ ഇവിടെത്തന്നെയുണ്ട്."
            replies = [
                "Always a pleasure to be of assistance, sir.",
                "Glad to be of service, sir.",
                "Happy to help, sir. Standing by."
            ]
            return random.choice(replies)

        if "തമാശ" in q or "joke" in q:
            if any('\u0d00' <= c <= '\u0d7f' for c in q):
                ml_jokes = [
                    "പ്രോഗ്രാമർമാർ എന്തുകൊണ്ടാണ് ഇരുണ്ട മുറികൾ ഇഷ്ടപ്പെടുന്നത്? കാരണം വെളിച്ചം ഉണ്ടെങ്കിൽ ബഗ്ഗുകൾ വരും, സാർ!",
                    "ലോകത്ത് രണ്ട് തരം ആളുകളുണ്ട്: ബൈനറി മനസ്സിലാകുന്നവരും, മനസ്സിലാകാത്തവരും!",
                    "ഞാൻ കമ്പ്യൂട്ടറിനോട് ഒരു തമാശ ചോദിച്ചു. അത് എന്റെ സ്വന്തം സെർച്ച് ഹിസ്റ്ററി എനിക്ക് കാണിച്ചു തന്നു!"
                ]
                return random.choice(ml_jokes)
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs, sir.",
                "There are 10 types of people in the world: those who understand binary, and those who don't.",
                "An artificial intelligence walked into a bar. The bartender asks, 'What'll you have?' The AI replies, 'Everything in the world, one token at a time.'",
                "I asked my computer for a joke. It showed me my own search history."
            ]
            return random.choice(jokes)

        if any(g in q for g in ["എന്തൊക്കെ ചെയ്യാൻ കഴിയും", "എന്തൊക്കെ ചെയ്യാൻ പറ്റും", "what can you do", "help", "commands"]):
            if any('\u0d00' <= c <= '\u0d7f' for c in q):
                return (
                    "ആപ്ലിക്കേഷനുകൾ തുറക്കാനും, ശബ്ദവും മീഡിയയും നിയന്ത്രിക്കാനും, സ്ക്രീൻഷോട്ട് എടുക്കാനും, "
                    "സിപിയു-റാം വിവരങ്ങൾ നൽകാനും, യൂട്യൂബിലും ഗൂഗിളിലും വിവരങ്ങൾ തിരയാനും, ചോദ്യങ്ങൾക്ക് മറുപടി നൽകാനും എനിക്ക് കഴിയും. "
                    "എപ്പോൾ വേണമെങ്കിലും എന്നെ വിളിക്കാം, സാർ."
                )
            return (
                "I can open applications, control media and volume, capture screenshots, monitor system CPU, RAM and battery, "
                "search Google and YouTube, record notes, lock your workstation, and answer questions. Simply summon me anytime."
            )

    def quick_offline_match(self, query: str) -> str | None:
        """Instant sub-millisecond match for identity, greetings, time, date, and math."""
        q = query.lower().strip()

        # Math detection
        if any(w in q for w in ["calculate", "multiply", "plus", "minus", "divided by", "times", "multiplied by", "into", " + ", " - ", " * ", " / "]) or re.match(r'^[\d\s+\-*/()^.]+$', q):
            math_ans = self.calculate_math(q)
            if math_ans:
                return math_ans

        # Quick greetings and identity checks
        if any(g in q for g in ["can you hear me", "are you listening", "am i audible"]):
            return "Yes, sir! I hear you loud and clear. All acoustic sensors are fully operational."
        if any(g in q for g in ["കേൾക്കാമോ", "കേൾക്കുന്നുണ്ടോ", "ശബ്ദം കേൾക്കുന്നുണ്ടോ"]):
            return "തീർച്ചയായും സാർ! ഞാൻ വ്യക്തമായി കേൾക്കുന്നുണ്ട്. എല്ലാ ഓഡിയോ സെൻസറുകളും പൂർണ്ണമായി പ്രവർത്തനക്ഷമമാണ്."

        # Instant Time & Date matching
        if any(t in q for t in ["what time", "whats the time", "what's the time", "what is the time", "current time", "the time", "time right now", "time now"]) or q in ["time", "the time"]:
            import datetime
            t_str = datetime.datetime.now().strftime("%I:%M %p").lstrip("0")
            return f"It is currently {t_str}, sir."

        if any(t in q for t in ["സമയം എത്രയായി", "ഇപ്പോഴത്തെ സമയം", "സമയം പറ", "സമയം എന്താണ്"]) or q in ["സമയം", "ക്ലോക്ക്"]:
            from jarvis.actions.system_control import system_controller
            return system_controller.get_time_malayalam()

        if any(t in q for t in ["what date", "whats the date", "what's the date", "what day is it", "what day is today", "today's date", "todays date", "date today"]) or q in ["date", "the date", "day today"]:
            import datetime
            d_str = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {d_str}, sir."

        if any(t in q for t in ["ഇന്നത്തെ തീയതി", "തീയതി എത്രയാണ്", "ഇന്ന് ഏത് ദിവസമാണ്", "തീയതി പറ"]) or q in ["തീയതി", "ഇന്ന്"]:
            from jarvis.actions.system_control import system_controller
            return system_controller.get_date_malayalam()

        if any(g in q for g in ["are you there", "you there"]):
            return "Always right here, sir. Standing by for your instructions."
        if any(g in q for g in ["അവിടെ ഉണ്ടോ", "ഇവിടെ ഉണ്ടോ"]):
            return "ഞാൻ ഇവിടെത്തന്നെയുണ്ട് സാർ. നിങ്ങളുടെ നിർദ്ദേശങ്ങൾക്കായി കാത്തിരിക്കുന്നു."

        if any(g == q for g in ["hello", "hi", "hey", "good morning", "good evening", "good afternoon"]):
            return "Hello, sir! How may I assist you today?"
        if any(g == q for g in ["നമസ്കാരം", "ഹലോ", "ഹായ്", "സുപ്രഭാതം"]):
            return "നമസ്കാരം സാർ! ഞാൻ മാണി. ഞാൻ എങ്ങനെ സഹായിക്കണം?"

        if any(g in q for g in ["who are you", "what are you", "introduce yourself"]):
            return (
                f"I am {config.ASSISTANT_NAME}, an advanced personal artificial intelligence system designed to manage your computer, "
                "automate your tasks, and assist you in any endeavor. At your service, sir."
            )
        if any(g in q for g in ["നീ ആരാണ്", "ആരാണ് നീ", "നിങ്ങൾ ആരാണ്", "ആരാണ് നിങ്ങൾ"]):
            return (
                f"ഞാൻ {config.ASSISTANT_NAME}, നിങ്ങളുടെ കമ്പ്യൂട്ടർ നിയന്ത്രിക്കാനും വിവരങ്ങൾ നൽകാനും രൂപകൽപ്പന ചെയ്ത "
                "പേഴ്സണൽ ആർട്ടിഫിഷ്യൽ ഇന്റലിജൻസ് അസിസ്റ്റന്റ് ആണ്. നിങ്ങളുടെ സേവനത്തിനായി ഞാൻ എപ്പോഴും സജ്ജനാണ്, സാർ."
            )
            
        if any(g in q for g in ["who made you", "who created you"]):
            return f"I am {config.ASSISTANT_NAME}, tailored right here to be your dedicated desktop companion."
        if any(g in q for g in ["ആരാണ് ഉണ്ടാക്കിയത്", "നിങ്ങളെ ആരാണ് ഉണ്ടാക്കിയത്"]):
            return f"ഞാൻ {config.ASSISTANT_NAME}, നിങ്ങളുടെ ഡെസ്ക്ടോപ്പ് സഹായിയായി രൂപകൽപ്പന ചെയ്യപ്പെട്ടതാണ്, സാർ."

        return None

    def ask(self, query: str) -> str:
        """Route instant queries locally (<1ms) and route general intelligence to Gemini."""
        quick = self.quick_offline_match(query)
        if quick:
            return quick

        llm_response = self.query_llm(query)
        if llm_response:
            return llm_response

        return self.offline_respond(query)

    def stream_ask(self, query: str):
        """Streaming version of ask(): yields instant offline matches immediately, or streams LLM sentences."""
        quick = self.quick_offline_match(query)
        if quick:
            yield quick
            return

        yield from self.stream_query_llm(query)

brain = JarvisBrain()

