import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis.voice.listener import listener
from jarvis.brain.intent_router import intent_router
from jarvis.brain.llm_client import brain
from jarvis.voice.speaker import speaker
from jarvis.config import config

def test_normalization():
    print("[*] Testing Acoustic Normalization...")
    assert listener._normalize_command_text("open you tube") == "open youtube"
    assert listener._normalize_command_text("open browser it") == "open browser"
    assert listener._normalize_command_text("open google chrome") == "open chrome"
    assert listener._normalize_command_text("launch vs code") == "launch vscode"
    print("[PASS] Normalization")

def test_youtube_and_browser_commands():
    print("[*] Testing YouTube & Browser Routing (32 Variations)...")
    yt_commands = [
        "open youtube", "open you tube", "open the youtube", "youtube", "launch youtube",
        "start youtube", "go to youtube", "open youtube.com", "youtube please", "can you open youtube",
        "please open youtube", "open youtube for me", "i want to open youtube", "open up youtube",
        "play youtube", "show me youtube", "open youtube website", "open youtube page",
        "open browser", "open the browser", "browser", "launch browser", "start browser",
        "open web browser", "open internet", "open chrome", "open google chrome", "chrome",
        "chrome browser", "open my browser", "can you open browser", "open browser please"
    ]
    for cmd in yt_commands:
        res = intent_router.process(cmd)
        assert res["action"] in ("website", "launch"), f"Failed for '{cmd}': got {res['action']} (reply: {res.get('response')})"
        assert any(w in res["response"].lower() for w in ["youtube", "chrome", "edge", "google", "accessing", "opening", "launching"]), f"Unexpected reply for '{cmd}': {res['response']}"

    # YouTube search
    res_search = intent_router.process("play interstellar on youtube")
    assert res_search["action"] == "youtube"
    assert "interstellar" in res_search["response"].lower()

    # YouTube search via open and search
    res_search2 = intent_router.process("search for quantum computing on youtube")
    assert res_search2["action"] == "youtube"
    assert "quantum" in res_search2["response"].lower()

    print(f"[PASS] All {len(yt_commands)} YouTube & Browser Variations Obeyed Successfully!")

def test_standby_direct_actions():
    print("[*] Testing Standby Direct Action Obedience...")
    direct_cmds = [
        "open youtube", "open browser", "youtube", "take a screenshot",
        "what time is it", "mute", "unmute", "system status", "today's date",
        "open chrome", "open notepad"
    ]
    for cmd in direct_cmds:
        is_act, res = intent_router.check_direct_action(cmd)
        assert is_act is True, f"Failed direct action detection for '{cmd}'"
        assert res["action"] != "conversation", f"Failed: action was conversation for '{cmd}'"

    # Non-action queries should require wake word
    ambient_speech = [
        "hello how are you", "what is quantum computing", "how far is the moon"
    ]
    for q in ambient_speech:
        is_act, _ = intent_router.check_direct_action(q)
        assert is_act is False, f"Ambient phrase should not trigger direct action: '{q}'"

    print(f"[PASS] Standby Direct Action Obedience Tested ({len(direct_cmds)} actions, {len(ambient_speech)} ambient)")

def test_gemini_fast_validation():
    print("[*] Testing Gemini Key Fast Verification & Timeout Safety...")
    import time
    t0 = time.time()
    success, msg = brain.set_gemini_api_key(config.GEMINI_API_KEY)
    elapsed = time.time() - t0
    assert success, f"Gemini validation failed: {msg}"
    assert elapsed < 15.0, f"Validation took too long ({elapsed:.2f}s > 15s)"
    print(f"[PASS] Gemini Key Verified in {elapsed*1000:.0f}ms")

def test_elevenlabs_settings_and_fallback():
    print("[*] Testing ElevenLabs Configuration & Fallback...")
    config.save_elevenlabs_settings("", "pNInz6obpgDQGcFmaJgB")
    assert config.ELEVENLABS_API_KEY == ""
    assert config.ELEVENLABS_VOICE_ID == "pNInz6obpgDQGcFmaJgB"

    cpath = speaker._get_cache_path("Test voice response")
    assert cpath.suffix == ".mp3"
    print("[PASS] ElevenLabs Settings & Fallback")

if __name__ == "__main__":
    import traceback
    try:
        print("=" * 60)
        print("Testing Speech Accuracy, Command Obeying & ElevenLabs Voice")
        print("=" * 60)
        test_normalization()
        test_youtube_and_browser_commands()
        test_standby_direct_actions()
        test_gemini_fast_validation()
        test_elevenlabs_settings_and_fallback()
        print("\nALL SPEECH AND VOICE TESTS PASSED!")
        sys.exit(0)
    except Exception as e:
        print(f"\n[TEST FAILED] {e}")
        traceback.print_exc()
        sys.exit(1)
