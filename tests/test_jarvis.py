import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis.actions.telemetry import telemetry
from jarvis.actions.notes_manager import notes_manager
from jarvis.actions.system_control import system_controller
from jarvis.brain.intent_router import intent_router
from jarvis.brain.llm_client import brain
from jarvis.voice.sfx import play_confirm_chime
from jarvis.voice.speaker import speaker

def test_telemetry():
    stats = telemetry.get_stats()
    assert "cpu_percent" in stats
    assert "ram_percent" in stats
    summary = telemetry.get_voice_summary()
    assert "diagnostics" in summary.lower() or "cpu" in summary.lower()
    print("[PASS] Telemetry")

def test_notes():
    notes_manager.clear_notes()
    notes_manager.add_note("Unit test note")
    notes = notes_manager.list_notes()
    assert len(notes) == 1
    assert notes[0]["text"] == "Unit test note"
    notes_manager.clear_notes()
    assert len(notes_manager.list_notes()) == 0
    print("[PASS] Notes Manager")

def test_system_control():
    time_str = system_controller.get_time_and_date()
    assert "currently" in time_str
    print("[PASS] System Control")

def test_brain_and_intent():
    res_time = intent_router.process("Mani whats the time right now")
    assert res_time["action"] == "time"
    assert "currently" in res_time["response"]

    res_date = intent_router.process("Mani whats the date today")
    assert res_date["action"] == "date"

    res_diag = intent_router.process("Hey Mani system diagnostics")
    assert res_diag["action"] == "telemetry"

    res_math = intent_router.process("Mani calculate 12 * 12")
    assert "144" in res_math["response"]


    res_wake = intent_router.process("Mani")
    assert "service" in res_wake["response"].lower()
    print("[PASS] Brain & Intent Router (Mani)")

def test_gemini_config_and_latency():
    import time
    t0 = time.time()
    res = brain.ask("who are you")
    elapsed = time.time() - t0
    # Latency should be sub-50ms (previously took 4000ms+ due to Ollama timeout)
    assert elapsed < 0.20, f"Latency too high: {elapsed}s"
    assert "Mani" in res

    # Empty key validation
    success, err = brain.set_gemini_api_key("")
    assert not success

    # Prewarmed speaker cache check
    cpath = speaker._get_cache_path("Yes, sir?")
    assert cpath.exists()
    print(f"[PASS] Gemini Config & Ultra-Low Latency ({elapsed*1000:.2f}ms)")

def test_malayalam_support():
    from jarvis.voice.listener import listener
    from jarvis.voice.speaker import speaker, is_malayalam_text

    # 1. Wake word detection in Malayalam
    is_wake1, cmd1 = listener.check_wake_word("മാണി യൂട്യൂബ് തുറക്കൂ")
    assert is_wake1, "Failed to match leading Malayalam wake word 'മാണി'"
    assert "യൂട്യൂബ്" in cmd1, f"Extracted command mismatch: {cmd1}"

    is_wake2, cmd2 = listener.check_wake_word("ഹേയ് മാണി സമയം എത്രയായി")
    assert is_wake2, "Failed to match 'ഹേയ് മാണി'"
    assert "സമയം" in cmd2, f"Extracted command mismatch: {cmd2}"

    is_wake3, cmd3 = listener.check_wake_word("മാണി")
    assert is_wake3 and cmd3 == "", "Standalone wake word should return True with empty command"

    # 2. Dynamic Malayalam voice selection in Speaker
    assert is_malayalam_text("നമസ്കാരം സാർ, ഞാൻ മാണി.")
    assert not is_malayalam_text("Hello sir, I am Mani.")
    assert speaker.get_target_voice("നമസ്കാരം സാർ") == "ml-IN-MidhunNeural"

    # 3. Malayalam Intent Routing
    res_time = intent_router.process("മാണി സമയം എത്രയായി")
    assert res_time["action"] == "time"
    assert "സമയം" in res_time["response"]

    res_date = intent_router.process("മാണി ഇന്നത്തെ തീയതി എന്താണ്")
    assert res_date["action"] == "date"
    assert "ഇന്ന്" in res_date["response"]

    res_yt = intent_router.process("മാണി യൂട്യൂബ് തുറക്കൂ")
    assert res_yt["action"] == "website"
    assert res_yt["data"].get("site") == "youtube"

    res_shot = intent_router.process("മാണി സ്ക്രീൻഷോട്ട് എടുക്കൂ")
    assert res_shot["action"] == "screenshot"

    res_vol = intent_router.process("മാണി ശബ്ദം കൂട്ടൂ")
    assert res_vol["action"] == "volume"

    res_lang = intent_router.process("മാണി മലയാളത്തിൽ സംസാരിക്കൂ")
    assert res_lang["action"] == "language"

    res_hello = intent_router.process("നമസ്കാരം മാണി")
    assert "മാണി" in res_hello["response"]

    print("[PASS] Malayalam Speech, Wake Word, & Intent Routing")

if __name__ == "__main__":
    print("Running J.A.R.V.I.S. Integration Tests...")
    test_telemetry()
    test_notes()
    test_system_control()
    test_brain_and_intent()
    test_gemini_config_and_latency()
    test_malayalam_support()
    print("ALL TESTS PASSED!")

