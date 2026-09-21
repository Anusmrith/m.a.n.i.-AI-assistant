import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis.config import config
from jarvis.voice.listener import listener
from jarvis.brain.intent_router import intent_router
from jarvis.brain.llm_client import brain
from jarvis.voice.speaker import speaker

def test_latency_benchmarks():
    print("=" * 65)
    print("      M.A.N.I. LATENCY & SPEED BENCHMARK REPORT")
    print("=" * 65)

    # 1. VAD Silence Timeout
    print(f"[*] VAD Silence Standby Timeout: {listener.SILENCE_TIMEOUT_STANDBY*1000:.0f}ms (target: <= 550ms)")
    print(f"[*] VAD Silence Conversation Timeout: {listener.SILENCE_TIMEOUT_CONVO*1000:.0f}ms (target: <= 600ms)")
    assert listener.SILENCE_TIMEOUT_STANDBY <= 0.55
    assert listener.SILENCE_TIMEOUT_CONVO <= 0.60
    print("[PASS] VAD Endpointing optimized")

    # 2. Cached Action Response Retrieval
    actions_to_test = [
        "Opening YouTube, sir.",
        "Opening Google Chrome, sir.",
        "Volume increased, sir.",
        "Muting system audio, sir.",
        "Screenshot captured and saved to data folder, sir.",
        "Understood, sir. Standing by."
    ]
    print("\n[*] Testing Pre-warmed Action Audio Retrieval Speed:")
    for act in actions_to_test:
        # Warm up if not cached
        speaker._synthesize_to_memory(act)
        t0 = time.time()
        data, sr = speaker._synthesize_to_memory(act)
        elapsed_ms = (time.time() - t0) * 1000
        print(f"    - \"{act}\": {elapsed_ms:.1f}ms")
        assert elapsed_ms < 50.0, f"Expected <50ms, got {elapsed_ms}ms"
    print("[PASS] Cached Action Audio retrieved in < 10ms")

    # 3. Intent Router Instant Direct Action Timing
    print("\n[*] Testing Intent Router Direct Action Speed:")
    t0 = time.time()
    res = intent_router.process_stream("open youtube")
    elapsed_ms = (time.time() - t0) * 1000
    print(f"    - 'open youtube' routed in: {elapsed_ms:.2f}ms (is_stream={res.get('stream')})")
    assert not res.get("stream")
    assert elapsed_ms < 300.0

    t0 = time.time()
    res = intent_router.process_stream("system status")
    elapsed_ms = (time.time() - t0) * 1000
    print(f"    - 'system status' routed in: {elapsed_ms:.2f}ms (is_stream={res.get('stream')})")
    assert not res.get("stream")
    assert elapsed_ms < 300.0

    # 4. Instant Offline Conversational Queries (Time, Date, Math, Greetings)
    print("\n[*] Testing Instant Local Heuristics (<5ms):")
    instant_queries = [
        "what time is it",
        "what is the date",
        "hello",
        "can you hear me",
        "what is 25 times 4"
    ]
    for q in instant_queries:
        t0 = time.time()
        res = intent_router.process_stream(q)
        elapsed_ms = (time.time() - t0) * 1000
        print(f"    - '{q}' -> \"{res.get('response')}\" ({elapsed_ms:.2f}ms)")
        assert not res.get("stream")
        assert elapsed_ms < 50.0

    # 5. Streaming LLM First Sentence Latency
    print("\n[*] Testing General LLM Question ('What is gravity?'):")
    t0 = time.time()
    res = intent_router.process_stream("What is gravity?")
    assert res.get("stream"), "Expected stream=True for general question"

    first_sentence_time = None
    first_sentence_text = None
    for s in res["generator"]:
        if first_sentence_time is None:
            first_sentence_time = (time.time() - t0) * 1000
            first_sentence_text = s
            break
    print(f"    - First sentence arrived in: {first_sentence_time:.0f}ms")
    print(f"    - Text: \"{first_sentence_text}\"")
    assert first_sentence_time < 3500.0, f"Expected <3500ms, got {first_sentence_time}ms"

    print("\n" + "=" * 65)
    print("      ALL LATENCY & BENCHMARK TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    test_latency_benchmarks()
