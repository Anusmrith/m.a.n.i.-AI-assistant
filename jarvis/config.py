import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables explicitly from project .env
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

DATA_DIR = BASE_DIR / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
CACHE_DIR = DATA_DIR / "cache"
NOTES_FILE = DATA_DIR / "notes.json"

for folder in [DATA_DIR, SCREENSHOTS_DIR, CACHE_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

class Config:
    ASSISTANT_NAME: str = os.getenv("JARVIS_NAME", "Mani")
    WAKE_WORDS: list[str] = [
        "mani",
        "hey mani",
        "he mani",
        "hi mani",
        "hello mani",
        "okay mani",
        "ok mani",
        "wake up mani",
        "money",
        "hey money",
        "he money",
        "hi money",
        "hello money",
        "ok money",
        "okay money",
        "wake up money",
        "many",
        "hey many",
        "he many",
        "manny",
        "hey manny",
        "jarvis",
        "hey jarvis",
        # Malayalam wake words (മലയാളം)
        "മാണി",
        "ഹേയ് മാണി",
        "ഹലോ മാണി",
        "മണി",
        "ഹേയ് മണി",
        "മാനി",
        "ഹേയ് മാനി",
        "ഹലോ മാനി",
        "മാണി ബ്രോ",
        "മണി ബ്രോ"
    ]
    
    # Voice configuration (Edge-TTS voices)
    # English default: en-GB-RyanNeural (authentic movie JARVIS voice)
    VOICE: str = os.getenv("JARVIS_VOICE", "en-GB-RyanNeural")
    VOICE_PITCH: str = os.getenv("JARVIS_VOICE_PITCH", "+0Hz")
    VOICE_RATE: str = os.getenv("JARVIS_VOICE_RATE", "+5%")

    # Malayalam default: ml-IN-MidhunNeural (natural male Indian Malayalam voice)
    MALAYALAM_VOICE: str = os.getenv("JARVIS_MALAYALAM_VOICE", "ml-IN-MidhunNeural")
    MALAYALAM_VOICE_FEMALE: str = "ml-IN-SobhanaNeural"
    
    # Audio settings (will auto-detect from default microphone device)
    SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "44100"))
    CHANNELS: int = int(os.getenv("CHANNELS", "2"))
    ENERGY_THRESHOLD: int = int(os.getenv("ENERGY_THRESHOLD", "250"))
    AUDIO_LANGUAGE: str = os.getenv("AUDIO_LANGUAGE", "ml-IN")
    MIC_INDEX: int | None = None  # None for default system microphone
    
    # Server settings
    HOST: str = os.getenv("JARVIS_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("JARVIS_PORT", "8000"))
    
    # AI Brain keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OLLAMA_ENABLED: bool = os.getenv("OLLAMA_ENABLED", "false").lower() in ("true", "1", "yes")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    
    # ElevenLabs Voice settings
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam (deep, authoritative)
    ELEVENLABS_MODEL_ID: str = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")

    # Persona Prompt - Bilingual English & Malayalam
    SYSTEM_PROMPT: str = (
        "You are M.A.N.I. (മാണി), an elite, highly capable personal AI "
        "serving as a dedicated desktop assistant for your user. "
        "You are fully bilingual and fluent in both Malayalam (മലയാളം) and English. "
        "When the user speaks or queries in Malayalam, ALWAYS respond in fluent, natural Malayalam. "
        "In Malayalam, address the user respectfully with 'സാർ' (or 'സർ'). "
        "When the user speaks or queries in English, respond in English, addressing them as 'sir'. "
        "Your tone is polite, refined, subtly witty, concise, and supremely confident. "
        "Keep your spoken replies direct and crisp, usually 1 to 3 sentences, unless the user asks for a detailed explanation. "
        "Never say you cannot interact with the computer—you have integrated automation protocols."
    )

    @classmethod
    def save_audio_language(cls, lang: str) -> bool:
        """Saves AUDIO_LANGUAGE to .env file and updates active runtime config."""
        clean_lang = lang.strip()
        cls.AUDIO_LANGUAGE = clean_lang
        os.environ["AUDIO_LANGUAGE"] = clean_lang

        env_path = BASE_DIR / ".env"
        lines = []
        found = False

        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("AUDIO_LANGUAGE="):
                        lines.append(f"AUDIO_LANGUAGE={clean_lang}\n")
                        found = True
                    else:
                        lines.append(line)

        if not found:
            lines.append(f"AUDIO_LANGUAGE={clean_lang}\n")

        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
        except Exception as e:
            print(f"[Config Error] Failed to write .env for AUDIO_LANGUAGE: {e}")
            return False

    @classmethod
    def save_gemini_api_key(cls, key: str) -> bool:
        """Saves GEMINI_API_KEY to .env file and updates active runtime config."""
        clean_key = key.strip()
        cls.GEMINI_API_KEY = clean_key
        os.environ["GEMINI_API_KEY"] = clean_key
        
        env_path = BASE_DIR / ".env"
        lines = []
        found = False
        
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        lines.append(f"GEMINI_API_KEY={clean_key}\n")
                        found = True
                    else:
                        lines.append(line)
                        
        if not found:
            lines.append(f"GEMINI_API_KEY={clean_key}\n")
            
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
        except Exception as e:
            print(f"[Config Error] Failed to write .env: {e}")
            return False

    @classmethod
    def save_elevenlabs_settings(cls, api_key: str, voice_id: str | None = None) -> bool:
        """Saves ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID to .env file."""
        clean_key = api_key.strip()
        cls.ELEVENLABS_API_KEY = clean_key
        os.environ["ELEVENLABS_API_KEY"] = clean_key
        if voice_id:
            cls.ELEVENLABS_VOICE_ID = voice_id.strip()
            os.environ["ELEVENLABS_VOICE_ID"] = voice_id.strip()

        env_path = BASE_DIR / ".env"
        lines = []
        found_key = False
        found_voice = False

        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("ELEVENLABS_API_KEY="):
                        lines.append(f"ELEVENLABS_API_KEY={clean_key}\n")
                        found_key = True
                    elif voice_id and line.startswith("ELEVENLABS_VOICE_ID="):
                        lines.append(f"ELEVENLABS_VOICE_ID={voice_id.strip()}\n")
                        found_voice = True
                    else:
                        lines.append(line)

        if not found_key:
            lines.append(f"ELEVENLABS_API_KEY={clean_key}\n")
        if voice_id and not found_voice:
            lines.append(f"ELEVENLABS_VOICE_ID={voice_id.strip()}\n")

        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
        except Exception as e:
            print(f"[Config Error] Failed to write .env for ElevenLabs: {e}")
            return False

config = Config()

