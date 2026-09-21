import time
import sys
import threading

# Reconfigure stdout and stderr for UTF-8 on Windows so Malayalam characters print smoothly without cp1252 charmap errors
try:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from jarvis.config import config
from jarvis.voice.listener import listener
from jarvis.voice.speaker import speaker
from jarvis.voice.sfx import play_confirm_chime
from jarvis.brain.intent_router import intent_router
from jarvis.actions.telemetry import telemetry
from jarvis.actions.system_control import system_controller
from jarvis.actions.notes_manager import notes_manager
from jarvis.ui.desktop_window import ManiDesktopApp

desktop_app = None

def handle_user_command(cmd_text: str):
    """Processes user command from voice or direct desktop UI input."""
    if not cmd_text or not cmd_text.strip():
        return

    print(f"\n[Commander]: {cmd_text}")
    if desktop_app:
        desktop_app.append_user_message(cmd_text)
        desktop_app.set_status("PROCESSING")

    # Execute through Intent Router
    result = intent_router.process(cmd_text)
    reply = result["response"]
    action = result.get("action")

    if desktop_app:
        desktop_app.append_assistant_message(reply, action)
        desktop_app.set_status("SPEAKING")

    # Speak response using neural voice
    speaker.speak(reply, block=True)

    if action in ("stop", "standby"):
        listener.end_conversation()
        if desktop_app:
            desktop_app.set_status("STANDBY")
    else:
        listener.refresh_conversation()
        if desktop_app:
            desktop_app.set_status("CONVERSATION")

def handle_trigger_mic():
    """Manual microphone listen trigger from desktop UI button."""
    play_wake_chime()
    listener.start_conversation()
    if desktop_app:
        desktop_app.set_status("LISTENING")

def handle_quick_action(action_name: str):
    """Handles quick action buttons from desktop UI."""
    if action_name == "telemetry":
        handle_user_command("system status")
    elif action_name == "screenshot":
        handle_user_command("take a screenshot")
    elif action_name == "mute":
        handle_user_command("mute")
    elif action_name == "notes":
        handle_user_command("read my notes")
    elif action_name == "lock":
        handle_user_command("lock pc")

def telemetry_loop():
    """Background publisher to update desktop telemetry every 2.5s."""
    while True:
        try:
            if desktop_app:
                stats = telemetry.get_stats()
                desktop_app.update_telemetry(stats)
        except Exception:
            pass
        time.sleep(2.5)

def main():
    global desktop_app

    print("=" * 65)
    print("      M.A.N.I. Desktop AI Assistant // Standby Mode")
    print("=" * 65)
    print(f"[*] Assistant Name: {config.ASSISTANT_NAME} (മാണി)")
    print("[*] Wake word: 'Mani', 'Hey Mani', 'മാണി', 'ഹേയ് മാണി'")
    print("[*] Continuous Conversation: ACTIVE (Say 'Mani' once to talk freely)")
    print(f"[*] Active Language: {config.AUDIO_LANGUAGE} (Bilingual: Malayalam & English)")
    print(f"[*] English Voice: {config.VOICE}")
    print(f"[*] Malayalam Voice: {config.MALAYALAM_VOICE}")
    print("[*] Real-time barge-in interruption enabled.")
    print("[*] Pure desktop mode: No external web browser needed.")
    print("=" * 65)

    # Initialize Native Desktop Window
    desktop_app = ManiDesktopApp(
        on_user_submit=handle_user_command,
        on_trigger_mic=handle_trigger_mic,
        on_quick_action=handle_quick_action
    )

    # Hook listener and speaker events to Native Desktop UI
    listener.register_callback(
        on_state_change=lambda st: desktop_app.set_status(st) if desktop_app else None,
        on_wake=lambda phrase: desktop_app.popup_and_focus() if desktop_app else None,
        on_sound_level=lambda rms: desktop_app.set_audio_level(rms) if desktop_app else None
    )

    speaker.register_callback(
        on_start=lambda txt: desktop_app.set_status("SPEAKING") if desktop_app else None,
        on_stop=lambda: desktop_app.set_status("CONVERSATION" if listener.in_conversation else "STANDBY") if desktop_app else None,
        on_chunk=lambda rms: desktop_app.set_audio_level(rms * 250) if desktop_app else None
    )

    # Start Background Telemetry Thread
    threading.Thread(target=telemetry_loop, daemon=True).start()

    # Start Background Wake-Word Listener Loop
    print("\n[+] Background microphone listener active. Say 'Mani' or 'മാണി' anytime!")
    print("[+] When Mani speaks, simply speak to interrupt him immediately.\n")
    listener.start_background_loop(handle_user_command)

    # Play startup confirmation sound & welcome in active language
    play_confirm_chime()
    if config.AUDIO_LANGUAGE.startswith("ml"):
        startup_msg = f"നമസ്കാരം സാർ. സിസ്റ്റം പ്രവർത്തനസജ്ജമാണ്. {config.ASSISTANT_NAME} ഓൺലൈനിലുണ്ട്."
    else:
        startup_msg = f"Good day, sir. Systems initialized. {config.ASSISTANT_NAME} is online and at your service."
    speaker.speak(startup_msg, block=False)

    # Run Native Desktop Window Loop
    try:
        desktop_app.run()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[*] Shutting down M.A.N.I. subsystems...")
        listener.stop()
        speaker.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
