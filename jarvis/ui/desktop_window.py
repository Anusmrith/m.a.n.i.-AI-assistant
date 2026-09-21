import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import datetime
import ctypes
import webbrowser

from jarvis.config import config
from jarvis.brain.llm_client import brain


class ManiDesktopApp:
    def __init__(self, on_user_submit=None, on_trigger_mic=None, on_quick_action=None):
        self.on_user_submit = on_user_submit
        self.on_trigger_mic = on_trigger_mic
        self.on_quick_action = on_quick_action
        
        # High DPI awareness for Windows
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.root = tk.Tk()
        self.root.title("M.A.N.I. Personal Assistant")
        self.root.geometry("520x680")
        self.root.minsize(440, 560)
        self.root.configure(bg="#060a12")

        self._setup_styles()
        self._build_ui()

        # Bring window to front on launch so it does not hide behind the terminal
        try:
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(300, lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()
        except Exception:
            pass

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure colors
        style.configure("TProgressbar", thickness=6, troughcolor="#0d1527", background="#00f0ff")

    def _build_ui(self):
        # 1. Header Frame
        header = tk.Frame(self.root, bg="#0b1222", bd=0, padx=16, pady=12)
        header.pack(fill=tk.X, side=tk.TOP)

        title_frame = tk.Frame(header, bg="#0b1222")
        title_frame.pack(side=tk.LEFT)

        tk.Label(title_frame, text="◈ M.A.N.I.", font=("Segoe UI", 16, "bold"), fg="#00f0ff", bg="#0b1222").pack(anchor="w")
        tk.Label(title_frame, text="DESKTOP AI ASSISTANT", font=("Segoe UI", 8), fg="#647d9e", bg="#0b1222").pack(anchor="w")

        # Telemetry & Gemini Status in Header Right
        header_right = tk.Frame(header, bg="#0b1222")
        header_right.pack(side=tk.RIGHT)

        self.gemini_btn = tk.Button(
            header_right,
            text="⚡ GEMINI: CHECKING",
            font=("Segoe UI", 8, "bold"),
            bg="#1c1605",
            fg="#ffaa00",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2",
            activebackground="#00f0ff",
            activeforeground="#000000",
            command=self.show_api_key_dialog
        )
        self.gemini_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.elevenlabs_btn = tk.Button(
            header_right,
            text="🎙️ 11LABS: OFF ⚪" if not config.ELEVENLABS_API_KEY else "🎙️ 11LABS: ON 🟢",
            font=("Segoe UI", 8, "bold"),
            bg="#05241b" if config.ELEVENLABS_API_KEY else "#0d1b2a",
            fg="#00ffaa" if config.ELEVENLABS_API_KEY else "#00f0ff",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2",
            activebackground="#00f0ff",
            activeforeground="#000000",
            command=self.show_elevenlabs_dialog
        )
        self.elevenlabs_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.lang_btn = tk.Button(
            header_right,
            text="🌐 മലയാളം 🟢" if config.AUDIO_LANGUAGE.startswith("ml") else "🌐 ENGLISH 🔵",
            font=("Segoe UI", 8, "bold"),
            bg="#05241b" if config.AUDIO_LANGUAGE.startswith("ml") else "#0d1b2a",
            fg="#00ffaa" if config.AUDIO_LANGUAGE.startswith("ml") else "#00f0ff",
            relief=tk.FLAT,
            padx=8,
            pady=3,
            cursor="hand2",
            activebackground="#00f0ff",
            activeforeground="#000000",
            command=self.toggle_language
        )
        self.lang_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.telemetry_label = tk.Label(header_right, text="CPU: --% | RAM: --% | BAT: --%", font=("Consolas", 9), fg="#00ffaa", bg="#0f1c33", padx=8, pady=4)
        self.telemetry_label.pack(side=tk.LEFT)

        # 2. Status Banner (Glowing Indicator)
        self.status_frame = tk.Frame(self.root, bg="#081426", padx=12, pady=8)
        self.status_frame.pack(fill=tk.X, pady=(2, 6))

        self.status_dot = tk.Label(self.status_frame, text="●", font=("Segoe UI", 11), fg="#00ffaa", bg="#081426")
        self.status_dot.pack(side=tk.LEFT, padx=(4, 6))

        self.status_text = tk.Label(self.status_frame, text="STANDBY // Say \"Mani\" to speak", font=("Segoe UI", 10, "bold"), fg="#e0f2ff", bg="#081426")
        self.status_text.pack(side=tk.LEFT)

        # Live Audio Level Meter (Visualizer Bar)
        self.audio_meter = ttk.Progressbar(self.root, orient="horizontal", mode="determinate", maximum=100, style="TProgressbar")
        self.audio_meter.pack(fill=tk.X, padx=16, pady=(0, 6))

        # 3. Conversation Feed (Chat History)
        feed_frame = tk.Frame(self.root, bg="#060a12", padx=16)
        feed_frame.pack(fill=tk.BOTH, expand=True)

        self.feed_box = scrolledtext.ScrolledText(
            feed_frame,
            wrap=tk.WORD,
            bg="#090f1d",
            fg="#e0f2ff",
            insertbackground="#00f0ff",
            font=("Segoe UI", 10),
            bd=1,
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.feed_box.pack(fill=tk.BOTH, expand=True)
        self.feed_box.config(state=tk.DISABLED)

        # Configure chat message tags
        self.feed_box.tag_config("user_sender", foreground="#ffb700", font=("Segoe UI", 9, "bold"))
        self.feed_box.tag_config("user_body", foreground="#ffffff", font=("Segoe UI", 10))
        self.feed_box.tag_config("mani_sender", foreground="#00f0ff", font=("Segoe UI", 9, "bold"))
        self.feed_box.tag_config("mani_body", foreground="#cbe4ff", font=("Segoe UI", 10))
        self.feed_box.tag_config("timestamp", foreground="#506680", font=("Consolas", 8))
        self.feed_box.tag_config("badge", foreground="#00ffaa", font=("Segoe UI", 8, "bold"))

        # Initial Welcome Message in Feed
        self.append_assistant_message("Online and synchronized, sir. Speak \"Mani\" anytime or click Listen.")

        # 4. Quick Actions Dock
        dock_frame = tk.Frame(self.root, bg="#060a12", padx=16, pady=6)
        dock_frame.pack(fill=tk.X)

        def make_btn(parent, text, bg, fg, cmd):
            return tk.Button(parent, text=text, bg=bg, fg=fg, activebackground="#00f0ff", activeforeground="#000000", relief=tk.FLAT, font=("Segoe UI", 8, "bold"), padx=7, pady=4, cursor="hand2", command=cmd)

        self.mic_btn = make_btn(dock_frame, "🎙️ LISTEN", "#006644", "#ffffff", self._handle_mic_click)
        self.mic_btn.pack(side=tk.LEFT, padx=2)

        self.stop_btn = make_btn(dock_frame, "🛑 STOP", "#44111f", "#ff8899", self._handle_stop_click)
        self.stop_btn.pack(side=tk.LEFT, padx=2)

        make_btn(dock_frame, "🔑 GEMINI KEY", "#181432", "#b388ff", self.show_api_key_dialog).pack(side=tk.LEFT, padx=2)
        make_btn(dock_frame, "📊 STATUS", "#0e182b", "#e0f2ff", lambda: self._quick_action("telemetry")).pack(side=tk.LEFT, padx=2)
        make_btn(dock_frame, "📸 SCREENSHOT", "#0e182b", "#e0f2ff", lambda: self._quick_action("screenshot")).pack(side=tk.LEFT, padx=2)
        make_btn(dock_frame, "🔇 MUTE", "#0e182b", "#e0f2ff", lambda: self._quick_action("mute")).pack(side=tk.LEFT, padx=2)
        make_btn(dock_frame, "🔒 LOCK", "#0e182b", "#ff5577", lambda: self._quick_action("lock")).pack(side=tk.RIGHT, padx=2)

        self.root.bind("<Escape>", lambda e: self._handle_stop_click())
        self.update_gemini_status()

        # 5. Bottom Direct Command Bar
        bottom_bar = tk.Frame(self.root, bg="#0b1222", padx=16, pady=10)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            bottom_bar,
            textvariable=self.entry_var,
            bg="#080e1a",
            fg="#ffffff",
            insertbackground="#00f0ff",
            font=("Segoe UI", 10),
            bd=1,
            relief=tk.FLAT
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=5)
        self.entry.bind("<Return>", self._handle_submit)

        send_btn = tk.Button(
            bottom_bar,
            text="RUN",
            bg="#0088cc",
            fg="#ffffff",
            activebackground="#00f0ff",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=4,
            command=self._handle_submit
        )
        send_btn.pack(side=tk.RIGHT)

    def _handle_submit(self, event=None):
        text = self.entry_var.get().strip()
        if not text:
            return
        self.entry_var.set("")
        if self.on_user_submit:
            threading.Thread(target=self.on_user_submit, args=(text,), daemon=True).start()

    def _handle_mic_click(self):
        if self.on_trigger_mic:
            threading.Thread(target=self.on_trigger_mic, daemon=True).start()

    def _handle_stop_click(self):
        from jarvis.voice.speaker import speaker
        from jarvis.voice.listener import listener
        speaker.stop()
        listener.end_conversation()
        self.set_status("STANDBY")

    def _quick_action(self, action_name):
        if self.on_quick_action:
            threading.Thread(target=self.on_quick_action, args=(action_name,), daemon=True).start()

    def popup_and_focus(self):
        """Brings the native window to front whenever Mani is called."""
        def _action():
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.attributes("-topmost", True)
                self.root.attributes("-topmost", False)
                self.set_status("LISTENING")
            except Exception:
                pass
        self.root.after(0, _action)

    def set_status(self, state: str):
        """Thread-safe status update."""
        def _action():
            st = state.upper()
            if st == "CONVERSATION":
                self.status_dot.config(text="●", fg="#00ffcc")
                self.status_text.config(text="CONVERSATION ACTIVE // Listening... (No need to say \"Mani\")", fg="#00ffcc")
                self.status_frame.config(bg="#042323")
                self.status_dot.config(bg="#042323")
                self.status_text.config(bg="#042323")
            elif st == "LISTENING":
                self.status_dot.config(text="●", fg="#00ffaa")
                self.status_text.config(text="HEARING YOU... // Listening...", fg="#00ffaa")
                self.status_frame.config(bg="#05241b")
                self.status_dot.config(bg="#05241b")
                self.status_text.config(bg="#05241b")
            elif st == "PROCESSING":
                self.status_dot.config(text="▲", fg="#ffaa00")
                self.status_text.config(text="PROCESSING... // Computing intent", fg="#ffaa00")
                self.status_frame.config(bg="#261b05")
                self.status_dot.config(bg="#261b05")
                self.status_text.config(bg="#261b05")
            elif st == "SPEAKING":
                self.status_dot.config(text="▶", fg="#00f0ff")
                self.status_text.config(text="SPEAKING... // (Speak anytime to interrupt)", fg="#00f0ff")
                self.status_frame.config(bg="#061c2e")
                self.status_dot.config(bg="#061c2e")
                self.status_text.config(bg="#061c2e")
            else:
                self.status_dot.config(text="●", fg="#507090")
                self.status_text.config(text="STANDBY // Say \"Mani\" into your microphone", fg="#a0b8d0")
                self.status_frame.config(bg="#081426")
                self.status_dot.config(bg="#081426")
                self.status_text.config(bg="#081426")
                self.audio_meter["value"] = 0
        self.root.after(0, _action)

    def set_audio_level(self, rms: float):
        """Thread-safe update of the live visualizer audio level bar."""
        def _action():
            val = min(100, max(0, int(rms / 4.0)))
            self.audio_meter["value"] = val
        self.root.after(0, _action)

    def append_user_message(self, text: str):
        """Thread-safe addition of user message."""
        def _action():
            now = datetime.datetime.now().strftime("%H:%M:%S")
            self.feed_box.config(state=tk.NORMAL)
            self.feed_box.insert(tk.END, f"\nCOMMANDER ", "user_sender")
            self.feed_box.insert(tk.END, f"[{now}]\n", "timestamp")
            self.feed_box.insert(tk.END, f"{text}\n", "user_body")
            self.feed_box.see(tk.END)
            self.feed_box.config(state=tk.DISABLED)
        self.root.after(0, _action)

    def append_assistant_message(self, text: str, action: str | None = None):
        """Thread-safe addition of Mani's response."""
        def _action():
            now = datetime.datetime.now().strftime("%H:%M:%S")
            self.feed_box.config(state=tk.NORMAL)
            self.feed_box.insert(tk.END, f"\nM.A.N.I. ", "mani_sender")
            if action and action != "conversation" and action != "standby":
                self.feed_box.insert(tk.END, f"[{action.upper()}] ", "badge")
            self.feed_box.insert(tk.END, f"[{now}]\n", "timestamp")
            self.feed_box.insert(tk.END, f"{text}\n", "mani_body")
            self.feed_box.see(tk.END)
            self.feed_box.config(state=tk.DISABLED)

            if action == "language":
                self.update_language_ui()
        self.root.after(0, _action)

    def toggle_language(self):
        """Toggle between Malayalam (ml-IN) and English (en-IN)."""
        current = config.AUDIO_LANGUAGE or "ml-IN"
        new_lang = "en-IN" if current.startswith("ml") else "ml-IN"
        config.save_audio_language(new_lang)
        self.update_language_ui()
        if new_lang.startswith("ml"):
            self.append_assistant_message("ഭാഷ മലയാളത്തിലേക്ക് മാറ്റിയിരിക്കുന്നു, സാർ.", "മലയാളം")
            from jarvis.voice.speaker import speaker
            speaker.speak("ഇനി മുതൽ ഞാൻ മലയാളത്തിൽ സംസാരിക്കാം, സാർ.", block=False)
        else:
            self.append_assistant_message("Language switched to English, sir.", "english")
            from jarvis.voice.speaker import speaker
            speaker.speak("Switched to English, sir.", block=False)

    def update_language_ui(self):
        """Updates the language toggle button state."""
        def _action():
            is_ml = config.AUDIO_LANGUAGE.startswith("ml")
            self.lang_btn.config(
                text="🌐 മലയാളം 🟢" if is_ml else "🌐 ENGLISH 🔵",
                bg="#05241b" if is_ml else "#0d1b2a",
                fg="#00ffaa" if is_ml else "#00f0ff"
            )
        self.root.after(0, _action)

    def update_telemetry(self, stats: dict):
        """Thread-safe update of CPU/RAM/Battery header stats."""
        def _action():
            cpu = stats.get("cpu_percent", 0)
            ram = stats.get("ram_percent", 0)
            bat = stats.get("battery_percent")
            bat_str = f"{bat}%" if bat is not None else "AC"
            self.telemetry_label.config(text=f"CPU: {cpu}% | RAM: {ram}% | BAT: {bat_str}")
        self.root.after(0, _action)
    def update_gemini_status(self):
        """Thread-safe update of Gemini connection badge."""
        def _action():
            if brain.is_gemini_connected():
                self.gemini_btn.config(text="⚡ GEMINI: ON 🟢", bg="#05241b", fg="#00ffaa")
            else:
                self.gemini_btn.config(text="⚡ GEMINI: SET KEY 🟡", bg="#261b05", fg="#ffaa00")
        self.root.after(0, _action)

    def show_api_key_dialog(self):
        """Display an intuitive, sleek modal dialog to configure Google Gemini API Key."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Google Gemini API Configuration")
        dialog.geometry("500x330")
        dialog.resizable(False, False)
        dialog.configure(bg="#080e1a")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center relative to root
        try:
            rx = self.root.winfo_x()
            ry = self.root.winfo_y()
            dialog.geometry(f"+{rx + 20}+{ry + 80}")
        except Exception:
            pass

        # Title / Description
        top_frame = tk.Frame(dialog, bg="#0b1426", padx=16, pady=12)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="🔑 Google Gemini AI Configuration", font=("Segoe UI", 12, "bold"), fg="#00f0ff", bg="#0b1426").pack(anchor="w")
        tk.Label(
            top_frame,
            text="Connect your free Gemini API key to enable limitless conversational\nintelligence, complex reasoning, and coding capabilities in Mani.",
            font=("Segoe UI", 9),
            fg="#8ba3c7",
            bg="#0b1426",
            justify=tk.LEFT
        ).pack(anchor="w", pady=(4, 0))

        # Status Line
        status_var = tk.StringVar()
        is_conn = brain.is_gemini_connected()
        status_var.set("🟢 Status: Gemini AI is CONNECTED and active." if is_conn else "🟡 Status: No API key configured. Mani is in offline heuristic mode.")
        status_lbl = tk.Label(dialog, textvariable=status_var, font=("Segoe UI", 9, "bold"), fg="#00ffaa" if is_conn else "#ffaa00", bg="#080e1a", padx=16, pady=8)
        status_lbl.pack(anchor="w")

        # Input Area
        input_frame = tk.Frame(dialog, bg="#080e1a", padx=16)
        input_frame.pack(fill=tk.X, pady=4)

        tk.Label(input_frame, text="Gemini API Key:", font=("Segoe UI", 9, "bold"), fg="#e0f2ff", bg="#080e1a").pack(anchor="w", pady=(0, 4))

        entry_row = tk.Frame(input_frame, bg="#080e1a")
        entry_row.pack(fill=tk.X)

        key_var = tk.StringVar(value=config.GEMINI_API_KEY or "")
        key_entry = tk.Entry(entry_row, textvariable=key_var, show="*", bg="#0e172a", fg="#ffffff", insertbackground="#00f0ff", font=("Consolas", 10), bd=1, relief=tk.FLAT)
        key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 6))

        # Show / Hide toggle button
        show_state = [False]
        def toggle_mask():
            show_state[0] = not show_state[0]
            key_entry.config(show="" if show_state[0] else "*")
            mask_btn.config(text="🙈 Hide" if show_state[0] else "👁️ Show")

        mask_btn = tk.Button(entry_row, text="👁️ Show", bg="#152238", fg="#9bc2f0", relief=tk.FLAT, font=("Segoe UI", 8), command=toggle_mask)
        mask_btn.pack(side=tk.LEFT, padx=(0, 4))

        def paste_clipboard():
            try:
                clip = dialog.clipboard_get().strip()
                if clip:
                    key_var.set(clip)
            except Exception:
                pass

        paste_btn = tk.Button(entry_row, text="📋 Paste", bg="#152238", fg="#00f0ff", relief=tk.FLAT, font=("Segoe UI", 8), command=paste_clipboard)
        paste_btn.pack(side=tk.LEFT)

        # Feedback / message
        msg_lbl = tk.Label(dialog, text="", font=("Segoe UI", 8), fg="#ff5577", bg="#080e1a", padx=16)
        msg_lbl.pack(anchor="w", pady=(2, 0))

        # Buttons Frame
        btn_frame = tk.Frame(dialog, bg="#080e1a", padx=16, pady=12)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        save_btn = None

        def do_save():
            nonlocal save_btn
            key = key_var.get().strip()
            if not key:
                msg_lbl.config(text="Please paste or enter your Gemini API key.", fg="#ff5577")
                return

            save_btn.config(state=tk.DISABLED, text="Validating...")
            msg_lbl.config(text="Testing API key connection to Google Gemini...", fg="#00f0ff")

            def _test_worker():
                success, message = brain.set_gemini_api_key(key)
                def _ui_update():
                    if success:
                        status_var.set("🟢 Status: Gemini AI connected and verified!")
                        status_lbl.config(fg="#00ffaa")
                        msg_lbl.config(text="Success! Saved to .env and activated.", fg="#00ffaa")
                        self.update_gemini_status()
                        self.append_assistant_message("Google Gemini intelligence engine connected and active, sir.", "gemini")
                        dialog.after(1400, dialog.destroy)
                    else:
                        save_btn.config(state=tk.NORMAL, text="💾 Save & Connect")
                        msg_lbl.config(text=f"Error: {message[:75]}", fg="#ff5577")
                dialog.after(0, _ui_update)

            threading.Thread(target=_test_worker, daemon=True).start()

        save_btn = tk.Button(
            btn_frame,
            text="💾 Save & Connect",
            bg="#0077b6",
            fg="#ffffff",
            activebackground="#00f0ff",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=do_save
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 8))

        def open_ai_studio():
            webbrowser.open("https://aistudio.google.com/app/apikey")

        key_help_btn = tk.Button(
            btn_frame,
            text="🌐 Get Free Key",
            bg="#111d33",
            fg="#8ab4f8",
            activebackground="#00f0ff",
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            padx=10,
            pady=6,
            cursor="hand2",
            command=open_ai_studio
        )
        key_help_btn.pack(side=tk.LEFT)

        close_btn = tk.Button(
            btn_frame,
            text="Close",
            bg="#1e2230",
            fg="#8899aa",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            command=dialog.destroy
        )
        close_btn.pack(side=tk.RIGHT)

    def update_elevenlabs_status(self):
        """Thread-safe update of ElevenLabs connection badge."""
        def _action():
            if config.ELEVENLABS_API_KEY:
                self.elevenlabs_btn.config(text="🎙️ 11LABS: ON 🟢", bg="#05241b", fg="#00ffaa")
            else:
                self.elevenlabs_btn.config(text="🎙️ 11LABS: OFF ⚪", bg="#0d1b2a", fg="#00f0ff")
        self.root.after(0, _action)

    def show_elevenlabs_dialog(self):
        """Display dialog to configure ElevenLabs API Key and Voice selection."""
        dialog = tk.Toplevel(self.root)
        dialog.title("ElevenLabs Neural Voice Configuration")
        dialog.geometry("520x420")
        dialog.resizable(False, False)
        dialog.configure(bg="#080e1a")
        dialog.transient(self.root)
        dialog.grab_set()

        try:
            rx = self.root.winfo_x()
            ry = self.root.winfo_y()
            dialog.geometry(f"+{rx + 20}+{ry + 60}")
        except Exception:
            pass

        # Title
        top_frame = tk.Frame(dialog, bg="#0b1426", padx=16, pady=12)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="🎙️ ElevenLabs Ultra-Realistic Neural Voice", font=("Segoe UI", 12, "bold"), fg="#00f0ff", bg="#0b1426").pack(anchor="w")
        tk.Label(
            top_frame,
            text="Enhance Mani with ElevenLabs' cutting-edge neural speech.\nIf no key is set, Mani uses the built-in authentic movie JARVIS voice (Edge-TTS).",
            font=("Segoe UI", 9),
            fg="#8ba3c7",
            bg="#0b1426",
            justify=tk.LEFT
        ).pack(anchor="w", pady=(4, 0))

        # Status
        status_var = tk.StringVar()
        is_active = bool(config.ELEVENLABS_API_KEY)
        status_var.set("🟢 Status: ElevenLabs Neural Voice is ACTIVE." if is_active else "⚪ Status: Using Built-in Edge-TTS JARVIS Voice.")
        status_lbl = tk.Label(dialog, textvariable=status_var, font=("Segoe UI", 9, "bold"), fg="#00ffaa" if is_active else "#00f0ff", bg="#080e1a", padx=16, pady=6)
        status_lbl.pack(anchor="w")

        # API Key Input
        input_frame = tk.Frame(dialog, bg="#080e1a", padx=16)
        input_frame.pack(fill=tk.X, pady=4)

        tk.Label(input_frame, text="ElevenLabs API Key:", font=("Segoe UI", 9, "bold"), fg="#e0f2ff", bg="#080e1a").pack(anchor="w", pady=(0, 4))
        entry_row = tk.Frame(input_frame, bg="#080e1a")
        entry_row.pack(fill=tk.X)

        key_var = tk.StringVar(value=config.ELEVENLABS_API_KEY or "")
        key_entry = tk.Entry(entry_row, textvariable=key_var, show="*", bg="#0e172a", fg="#ffffff", insertbackground="#00f0ff", font=("Consolas", 10), bd=1, relief=tk.FLAT)
        key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 6))

        show_state = [False]
        def toggle_mask():
            show_state[0] = not show_state[0]
            key_entry.config(show="" if show_state[0] else "*")
            mask_btn.config(text="🙈 Hide" if show_state[0] else "👁️ Show")

        mask_btn = tk.Button(entry_row, text="👁️ Show", bg="#152238", fg="#9bc2f0", relief=tk.FLAT, font=("Segoe UI", 8), command=toggle_mask)
        mask_btn.pack(side=tk.LEFT, padx=(0, 4))

        def paste_clipboard():
            try:
                clip = dialog.clipboard_get().strip()
                if clip:
                    key_var.set(clip)
            except Exception:
                pass

        paste_btn = tk.Button(entry_row, text="📋 Paste", bg="#152238", fg="#00f0ff", relief=tk.FLAT, font=("Segoe UI", 8), command=paste_clipboard)
        paste_btn.pack(side=tk.LEFT)

        # Voice Selector
        voice_frame = tk.Frame(dialog, bg="#080e1a", padx=16, pady=8)
        voice_frame.pack(fill=tk.X)

        tk.Label(voice_frame, text="Select Voice Preset or enter Custom Voice ID:", font=("Segoe UI", 9, "bold"), fg="#e0f2ff", bg="#080e1a").pack(anchor="w", pady=(0, 4))

        voices = [
            ("Adam (Deep JARVIS style)", "pNInz6obpgDQGcFmaJgB"),
            ("Daniel (British Butler)", "onwK4e9ZLuTAKqWW03F9"),
            ("Rachel (Warm & Conversational)", "21m00Tcm4TlvDq8ikWAM"),
            ("Josh (Young & Dynamic)", "TxGEqnHWrfWFTfGW9XjX")
        ]

        voice_var = tk.StringVar(value=config.ELEVENLABS_VOICE_ID or "pNInz6obpgDQGcFmaJgB")

        for label, vid in voices:
            rb = tk.Radiobutton(
                voice_frame,
                text=f"{label}",
                variable=voice_var,
                value=vid,
                bg="#080e1a",
                fg="#c0d4ec",
                selectcolor="#091428",
                activebackground="#080e1a",
                activeforeground="#00f0ff",
                font=("Segoe UI", 8)
            )
            rb.pack(anchor="w")

        custom_row = tk.Frame(voice_frame, bg="#080e1a")
        custom_row.pack(fill=tk.X, pady=(4, 0))
        tk.Label(custom_row, text="Custom Voice ID:", font=("Segoe UI", 8), fg="#8ba3c7", bg="#080e1a").pack(side=tk.LEFT, padx=(0, 6))
        custom_entry = tk.Entry(custom_row, textvariable=voice_var, bg="#0e172a", fg="#00f0ff", font=("Consolas", 8), bd=1, relief=tk.FLAT)
        custom_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        msg_lbl = tk.Label(dialog, text="", font=("Segoe UI", 8), fg="#00ffaa", bg="#080e1a", padx=16)
        msg_lbl.pack(anchor="w", pady=(2, 0))

        btn_frame = tk.Frame(dialog, bg="#080e1a", padx=16, pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        def do_save_elevenlabs():
            k = key_var.get().strip()
            v = voice_var.get().strip() or "pNInz6obpgDQGcFmaJgB"
            config.save_elevenlabs_settings(k, v)
            self.update_elevenlabs_status()
            if k:
                msg_lbl.config(text="ElevenLabs configuration saved! Testing voice...", fg="#00ffaa")
                status_var.set("🟢 Status: ElevenLabs Neural Voice is ACTIVE.")
                status_lbl.config(fg="#00ffaa")
                speaker.speak("ElevenLabs neural voice initialized, sir.", block=False)
            else:
                msg_lbl.config(text="Settings saved. Using built-in Edge-TTS voice.", fg="#ffaa00")
                status_var.set("⚪ Status: Using Built-in Edge-TTS JARVIS Voice.")
                status_lbl.config(fg="#00f0ff")
            dialog.after(1600, dialog.destroy)

        save_btn = tk.Button(
            btn_frame,
            text="💾 Save Voice Settings",
            bg="#0077b6",
            fg="#ffffff",
            activebackground="#00f0ff",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=6,
            cursor="hand2",
            command=do_save_elevenlabs
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 8))

        close_btn = tk.Button(
            btn_frame,
            text="Close",
            bg="#1e2230",
            fg="#8899aa",
            relief=tk.FLAT,
            padx=12,
            pady=6,
            command=dialog.destroy
        )
        close_btn.pack(side=tk.RIGHT)

    def run(self):
        """Start the Tkinter event loop."""
        self.root.mainloop()
