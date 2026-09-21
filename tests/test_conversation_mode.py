import sys
import time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis.voice.listener import listener
from jarvis.brain.intent_router import intent_router

def test_wake_word_extraction():
    print("[*] Testing Wake Word Detection & Extraction...")
    
    # 1. Standalone summon
    is_wake, cmd = listener.check_wake_word("Mani")
    assert is_wake and cmd == "", f"Failed: {cmd}"

    is_wake, cmd = listener.check_wake_word("hey mani")
    assert is_wake and cmd == "", f"Failed: {cmd}"

    # 2. Leading wake word with command
    is_wake, cmd = listener.check_wake_word("Mani what is the time")
    assert is_wake and cmd == "what is the time", f"Failed: {cmd}"

    is_wake, cmd = listener.check_wake_word("hey mani, can you open chrome")
    assert is_wake and cmd == "can you open chrome", f"Failed: {cmd}"

    # 3. Trailing wake word
    is_wake, cmd = listener.check_wake_word("what is the time mani")
    assert is_wake and cmd == "what is the time", f"Failed: {cmd}"

    # 4. Phonetic variants
    is_wake, cmd = listener.check_wake_word("money what is 10 plus 10")
    assert is_wake and cmd == "what is 10 plus 10", f"Failed: {cmd}"

    is_wake, cmd = listener.check_wake_word("many tell me a joke")
    assert is_wake and cmd == "tell me a joke", f"Failed: {cmd}"

    # 5. Non-wake speech
    is_wake, cmd = listener.check_wake_word("what is the weather today")
    assert not is_wake and cmd == "", f"Failed: {cmd}"

    print("[PASS] Wake Word Extraction")

def test_audio_normalization():
    print("[*] Testing Audio Normalization & Digital Gain...")
    
    # Quiet speech (peak 800) -> should be boosted with target_peak=22000 and max_gain=8
    quiet_signal = (np.sin(np.linspace(0, 50, 1600)) * 800).astype(np.int16)
    normalized = listener._normalize_audio(quiet_signal, target_peak=22000)
    peak = np.max(np.abs(normalized))
    assert peak > 4000, f"Normalization did not boost quiet audio: peak={peak}"
    assert peak <= 32767, f"Clipped: peak={peak}"

    # Pure silence / background noise (peak 100) -> should NOT be amplified (below threshold 200)
    silence = np.ones(100, dtype=np.int16) * 100
    norm_silence = listener._normalize_audio(silence, target_peak=22000)
    assert np.max(np.abs(norm_silence)) == 100, "Silence was erroneously amplified"

    # Already loud audio (peak 28000) -> should NOT clip
    loud = (np.sin(np.linspace(0, 50, 1600)) * 28000).astype(np.int16)
    norm_loud = listener._normalize_audio(loud, target_peak=22000)
    assert np.max(np.abs(norm_loud)) <= 32767

    print("[PASS] Audio Normalization")

def test_conversation_lifecycle():
    print("[*] Testing Continuous Conversation Lifecycle...")
    
    # Initially standby
    listener.end_conversation()
    assert not listener.in_conversation
    assert listener.state == "STANDBY"

    # Enter conversation (say Mani once)
    listener.start_conversation(duration=5.0)
    assert listener.in_conversation
    assert listener.state == "CONVERSATION"
    assert listener.conversation_expiry > time.time()

    # Refresh conversation (user asked another question)
    prev_expiry = listener.conversation_expiry
    time.sleep(0.05)
    listener.refresh_conversation(duration=8.0)
    assert listener.in_conversation
    assert listener.conversation_expiry > prev_expiry

    # Explicit exit (user said "that's all" / "thank you")
    listener.end_conversation()
    assert not listener.in_conversation
    assert listener.state == "STANDBY"

    print("[PASS] Conversation Lifecycle")

def test_intent_router_conversation_exit():
    print("[*] Testing Intent Router Dismissals & Exits...")

    exit_queries = [
        "that's all",
        "thats all",
        "that will be all",
        "thank you",
        "thanks mani",
        "goodbye",
        "bye",
        "go to sleep",
        "dismiss",
        "standby"
    ]

    for q in exit_queries:
        res = intent_router.process(q)
        assert res["action"] in ("standby", "stop"), f"Failed for '{q}': got {res['action']}"
        assert "standing by" in res["response"].lower() or "welcome" in res["response"].lower()

    # Normal command still works
    res_calc = intent_router.process("calculate 50 * 2")
    assert res_calc["action"] == "conversation" or "100" in res_calc["response"]

    print("[PASS] Intent Router Exits")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Continuous Conversation Mode & Audio Enhancements")
    print("=" * 60)
    test_wake_word_extraction()
    test_audio_normalization()
    test_conversation_lifecycle()
    test_intent_router_conversation_exit()
    print("\nALL CONVERSATION MODE TESTS PASSED SUCCESSFULLY!")
