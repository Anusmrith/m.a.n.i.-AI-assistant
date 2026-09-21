# M.A.N.I. Personal AI Assistant (Mark VII)

[![HUD Live Demo](https://img.shields.io/badge/Arc--Reactor%20HUD-Live%20Demo-00f0ff?style=for-the-badge&logo=github&logoColor=white)](https://anusmrith.github.io/m.a.n.i.-AI-assistant/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078d6?style=for-the-badge&logo=windows)](https://github.com/Anusmrith/m.a.n.i.-AI-assistant)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow?style=for-the-badge&logo=python)](https://www.python.org/)

A voice-activated, intelligent personal AI assistant inspired by Iron Man's J.A.R.V.I.S., designed specifically for Windows.

🌐 **Experience the Live Stark Industries Arc-Reactor HUD online:** [https://anusmrith.github.io/m.a.n.i.-AI-assistant/](https://anusmrith.github.io/m.a.n.i.-AI-assistant/)

---

## ⚡ Key Capabilities

1. **Continuous Conversation Voice Activation**:
   - Say **"Mani"** (or "Hey Mani") **just once** to start a conversation.
   - Once Mani wakes up and responds, he enters **Continuous Conversation Mode** for 10 seconds.
   - **You do NOT need to say "Mani" again** for follow-up questions or commands! Speak directly to him.
   - Every question refreshes the listening timer.
   - To finish, say *"that's all"*, *"thank you"*, *"bye"*, or simply pause for 10 seconds, and Mani gracefully returns to Standby.
   - Responds with an authentic high-tech rising chime and speaks back with a cinematic British neural voice (`en-GB-RyanNeural`).

2. **Windows Computer Control & Automation**:
   - **Launch Apps**: "Open Chrome", "Launch Spotify", "Open VS Code", "Start Calculator", "Open Notepad", etc.
   - **Volume & Audio**: "Mute", "Unmute", "Volume up", "Volume down", "Set volume to 50".
   - **Media Control**: "Play music", "Pause", "Next track", "Previous track".
   - **Desktop Control**: "Take a screenshot" (stored in `data/screenshots/` and previewed on the HUD), "Minimize windows" / "Show desktop", "Lock workstation".
   - **System Telemetry**: "System status" or "Diagnostics" reports CPU %, RAM %, Disk space, and Battery reserves.
   - **Web & YouTube**: "Search Google for ...", "Play Queen Bohemian Rhapsody on YouTube", "Open Reddit", "Open GitHub".
   - **Notes & Reminders**: "Take a note: ...", "Read my notes", "Clear all notes".
   - **Weather & Time**: "What time is it?", "What date is it?", "Weather in Tokyo".

3. **Stark Industries Arc-Reactor HUD**:
   - Holographic dark-mode interface with rotating concentric energy rings and glassmorphism.
   - Dynamic real-time Audio Visualizer ring pulsing to Mani's voice.
   - Live system telemetry gauges (CPU, RAM, Battery, Disk, Uptime) updating in real-time over WebSocket.
   - Neural transcript feed with screenshot previews and action badges.
   - One-click quick-action dock and command input.

4. **AI Intelligence Engine**:
   - Built-in Autonomous Offline Intelligence: handles math calculations, Wikipedia queries, jokes, system automation, and classic persona dialogues without requiring an API key.
   - (Optional) **Google Gemini API**: Connect your free Gemini API key in `.env` for unlimited conversational reasoning, coding help, and complex problem solving.
   - (Optional) **Ollama**: Connect a local LLM (e.g. Llama 3) seamlessly.

---

## 🚀 Quick Start

### 1. Launch Mani
Simply double-click:
```bash
start_mani.bat
```
(or `start_jarvis.bat`)

Or run from PowerShell / Command Prompt:
```bash
.venv\Scripts\python.exe run_jarvis.py
```

This will:
1. Start the FastAPI backend and WebSocket pipeline on `http://127.0.0.1:8000`.
2. Automatically launch the Arc-Reactor HUD in your default web browser.
3. Announce systems online in the neural voice: *"Good day, sir. Systems initialized. Mani is online and at your service."*
4. Begin monitoring your microphone for the wake word **"Mani"**.

---

## 🎙️ Spoken Command Examples

Say **"Mani"**, wait for the chime or reply, and speak your command, or say it in a single phrase:

| Category | Example Voice Commands |
|---|---|
| **System Diagnostics** | *"Mani, what's my system status?"* <br> *"Mani, check battery level."* <br> *"How is the CPU load?"* |
| **App Launcher** | *"Mani, open Chrome."* <br> *"Launch Spotify."* <br> *"Open VS Code."* <br> *"Start Calculator."* |
| **Volume & Media** | *"Mani, mute volume."* <br> *"Set volume to 40."* <br> *"Volume up."* <br> *"Next song."* <br> *"Pause music."* |
| **Workstation** | *"Mani, take a screenshot."* <br> *"Minimize all windows."* <br> *"Lock my PC."* |
| **Web & Media** | *"Mani, search YouTube for Interstellar soundtrack."* <br> *"Search Google for quantum computing."* <br> *"Open GitHub."* |
| **Notes** | *"Mani, take a note: Buy groceries at 7 PM."* <br> *"Read my notes."* <br> *"Clear notes."* |
| **General Knowledge** | *"Mani, who was Nikola Tesla?"* <br> *"Calculate 450 multiplied by 18."* <br> *"Tell me a joke."* <br> *"What time is it?"* <br> *"Weather in London."* |

---

## ⚙️ Configuration (`.env`)

To customize settings, edit `.env`:
```ini
JARVIS_NAME=Mani
JARVIS_VOICE=en-GB-RyanNeural
ENERGY_THRESHOLD=400
GEMINI_API_KEY=your_gemini_api_key_here
```
