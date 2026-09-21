import numpy as np
import sounddevice as sd
import threading

def _play_buffer(samples: np.ndarray, sample_rate: int = 44100):
    """Play sound array in a background thread to prevent blocking."""
    def _run():
        try:
            sd.play(samples, samplerate=sample_rate)
            sd.wait()
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()

def play_wake_chime():
    """Crisp high-tech rising chime when Jarvis is called."""
    sr = 44100
    duration = 0.18
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    
    # 587Hz (D5) to 880Hz (A5) frequency sweep with warm harmonics
    freq = np.linspace(587.33, 880.0, len(t))
    signal = 0.6 * np.sin(2 * np.pi * freq * t) + 0.2 * np.sin(4 * np.pi * freq * t)
    
    # Fast attack, exponential decay envelope
    envelope = np.exp(-12 * t / duration)
    envelope[:int(sr * 0.015)] = np.linspace(0, 1, int(sr * 0.015))
    
    audio = (signal * envelope).astype(np.float32)
    _play_buffer(audio, sr)

def play_confirm_chime():
    """Two-tone affirmative acknowledgment chime."""
    sr = 44100
    d1, d2 = 0.07, 0.12
    t1 = np.linspace(0, d1, int(sr * d1), endpoint=False)
    t2 = np.linspace(0, d2, int(sr * d2), endpoint=False)
    
    sig1 = 0.5 * np.sin(2 * np.pi * 659.25 * t1)  # E5
    env1 = np.exp(-10 * t1 / d1)
    
    sig2 = 0.6 * np.sin(2 * np.pi * 880.00 * t2)  # A5
    env2 = np.exp(-8 * t2 / d2)
    
    tone1 = (sig1 * env1).astype(np.float32)
    tone2 = (sig2 * env2).astype(np.float32)
    gap = np.zeros(int(sr * 0.02), dtype=np.float32)
    
    audio = np.concatenate([tone1, gap, tone2])
    _play_buffer(audio, sr)

def play_standby_chime():
    """Soft descending sci-fi power-down / sleep tone."""
    sr = 44100
    duration = 0.22
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    freq = np.linspace(783.99, 440.0, len(t))
    signal = 0.4 * np.sin(2 * np.pi * freq * t)
    envelope = np.exp(-8 * t / duration)
    audio = (signal * envelope).astype(np.float32)
    _play_buffer(audio, sr)
