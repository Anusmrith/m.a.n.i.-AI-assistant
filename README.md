# M.A.N.I. Personal AI Assistant (Mark VII)

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078d6?style=for-the-badge&logo=windows)](https://github.com/Anusmrith/m.a.n.i.-AI-assistant)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow?style=for-the-badge&logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](https://github.com/Anusmrith/m.a.n.i.-AI-assistant)

A voice-activated, intelligent personal AI assistant inspired by Iron Man's J.A.R.V.I.S., built specifically for Windows as a native desktop application.

---

## ⚡ Key Capabilities

1. **Continuous Conversation Voice Activation**:
   - Say **"Mani"** (or "Hey Mani") **just once** to start a conversation.
   - Once Mani wakes up and responds, he enters **Continuous Conversation Mode** for 10 seconds.
   - **You do NOT need to say "Mani" again** for follow-up questions or commands! Speak directly to him.
   - Every question refreshes the listening timer.
   - To finish, say *"that's all"*, *"thank you"*, *"bye"*, or simply pause for 10 seconds, and Mani gracefully returns to Standby.
   - Responds with an authentic high-tech rising chime and speaks back with a cinematic British neural voice (`en-GB-RyanNeural`) or Malayalam neural voice (`ml-IN-SobhanaNeural`).

2. **Windows Computer Control & Automation**:
   - **Launch Apps**: "Open Chrome", "Launch Spotify", "Open VS Code", "Start Calculator", "Open Notepad", etc.
   - **Volume & Audio**: "Mute", "Unmute", "Volume up", "Volume down", "Set volume to 50".
   - **Media Control**: "Play music", "Pause", "Next track", "Previous track".
   - **Desktop Control**: "Take a screenshot" (stored in `data/screenshots/` and previewed on the window), "Minimize windows" / "Show desktop", "Lock workstation".
   - **System Telemetry**: "System status" or "Diagnostics" reports CPU %, RAM %, Disk space, and Battery reserves.
   - **Web & YouTube**: "Search Google for ...", "Play Queen Bohemian Rhapsody on YouTube", "Open Reddit", "Open GitHub".
   - **Notes & Reminders**: "Take a note: ...", "Read my notes", "Clear all notes".
   - **Weather & Time**: "What time is it?", "What date is it?", "Weather in Tokyo".

3. **Native Windows Desktop Window**:
   - Sleek cyberpunk desktop companion window showing live CPU, RAM, Battery, and Disk telemetry.
   - Real-time conversation transcript and screenshot previews.
   - Quick Action buttons for instant 1-click execution.
   - Audio pulse meter reflecting spoken speech and microphone intensity.

4. **AI Intelligence Engine**:
   - Built-in Autonomous Offline Intelligence: handles math calculations, Wikipedia queries, jokes, system automation, and classic persona dialogues without requiring an API key.
   - (Optional) **Google Gemini API**: Connect your free Gemini API key in `.env` for unlimited conversational reasoning, coding help, and complex problem solving.
   - (Optional) **Ollama**: Connect a local LLM (e.g. Llama 3) seamlessly.

---

## 🚀 Quick Start (Windows)

### 1. Run from GitHub
Clone the repository and launch Mani:
```cmd
git clone https://github.com/Anusmrith/m.a.n.i.-AI-assistant.git
cd m.a.n.i.-AI-assistant
start_mani.bat
```

*(Or in PowerShell)*:
```powershell
git clone https://github.com/Anusmrith/m.a.n.i.-AI-assistant.git; cd m.a.n.i.-AI-assistant; .\start_mani.bat
```

### 2. What `start_mani.bat` Does Automatically:
`start_mani.bat` is an all-in-one launcher designed for seamless Windows execution:
- ✅ Checks for Python 3.10+ installation
- ✅ Automatically initializes a Python virtual environment (`.venv`) on first launch
- ✅ Installs all dependencies from `requirements.txt`
- ✅ Sets up your local `.env` configuration file from `.env.example`
- ✅ Starts the native Windows desktop companion window and activates voice listening!

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

Settings are stored in `.env` (automatically created from `.env.example` on first run):
```ini
JARVIS_NAME=Mani
JARVIS_VOICE=en-GB-RyanNeural
AUDIO_LANGUAGE=en-IN
ENERGY_THRESHOLD=400
GEMINI_API_KEY=your_gemini_api_key_here
```
