import os
import subprocess
import webbrowser
import datetime
import urllib.parse
import ctypes
from pathlib import Path
import pyautogui
import requests

from jarvis.config import SCREENSHOTS_DIR

pyautogui.FAILSAFE = False


class SystemController:
    def __init__(self):
        self.app_map = {
            "chrome": "chrome",
            "google chrome": "chrome",
            "edge": "msedge",
            "microsoft edge": "msedge",
            "brave": "brave",
            "firefox": "firefox",
            "browser": "chrome",
            "calculator": "calc",
            "calc": "calc",
            "notepad": "notepad",
            "notes": "notepad",
            "settings": "ms-settings:",
            "windows settings": "ms-settings:",
            "camera": "microsoft.windows.camera:",
            "store": "ms-windows-store:",
            "microsoft store": "ms-windows-store:",
            "explorer": "explorer",
            "file explorer": "explorer",
            "files": "explorer",
            "my computer": "explorer",
            "this pc": "explorer",
            "task manager": "taskmgr",
            "taskmgr": "taskmgr",
            "paint": "mspaint",
            "mspaint": "mspaint",
            "code": "code",
            "vscode": "code",
            "vs code": "code",
            "visual studio code": "code",
            "terminal": "wt",
            "windows terminal": "wt",
            "cmd": "cmd",
            "command prompt": "cmd",
            "powershell": "powershell",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "spotify": "spotify",
            "discord": "discord",
            "whatsapp": "whatsapp:",
            "telegram": "telegram:",
        }

    def find_installed_shortcut(self, app_name: str) -> str | None:
        """Search Windows Start Menu for an installed application shortcut (.lnk)."""
        clean = app_name.lower().strip()
        search_dirs = [
            os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs'),
            os.path.expandvars(r'%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs')
        ]
        exact_match = None
        partial_match = None
        for base_dir in search_dirs:
            if not os.path.exists(base_dir):
                continue
            for root, _, files in os.walk(base_dir):
                for f in files:
                    if f.lower().endswith('.lnk'):
                        base = f[:-4].lower()
                        if base == clean:
                            return os.path.join(root, f)
                        elif clean in base and not partial_match:
                            partial_match = os.path.join(root, f)
        return exact_match or partial_match

    def launch_app(self, app_name: str) -> tuple[bool, str]:
        """Launch desktop application safely with multiple fallback layers and zero system error popups."""
        import re
        clean_name = app_name.lower().strip()
        clean_name = re.sub(r'^(the|an|a)\s+', '', clean_name)
        clean_name = re.sub(r'\s+(application|app|program|software)$', '', clean_name).strip()

        # Handle generic requests where no specific app name was given
        generic_terms = ["", "application", "app", "apps", "program", "programs", "software", "an application", "the application", "any application"]
        if clean_name in generic_terms:
            return False, "Which application would you like me to open, sir? You can say Chrome, Notepad, Calculator, VS Code, Discord, or Android Studio."

        # 1. Check direct dictionary mapping
        target = self.app_map.get(clean_name)
        if not target:
            for key, val in self.app_map.items():
                if key in clean_name or clean_name in key:
                    target = val
                    clean_name = key
                    break

        if target:
            try:
                os.startfile(target)
                return True, f"Opening {clean_name.title()}, sir."
            except Exception:
                try:
                    subprocess.Popen(f'start "" "{target}"', shell=True)
                    return True, f"Opening {clean_name.title()}, sir."
                except Exception:
                    pass

        # 2. Check Windows Start Menu shortcuts
        shortcut = self.find_installed_shortcut(clean_name)
        if shortcut:
            try:
                os.startfile(shortcut)
                return True, f"Launching {clean_name.title()}, sir."
            except Exception as e:
                return False, f"Could not launch {clean_name}: {e}"

        # 3. Direct os.startfile attempt
        try:
            os.startfile(clean_name)
            return True, f"Launching {clean_name.title()}, sir."
        except Exception:
            # Cleanly inform user without any OS dialog popups
            return False, f"I could not locate '{clean_name}' on your system, sir. Please verify the application name."


    def control_volume(self, action: str, level: int | None = None) -> str:
        """Control Windows system volume."""
        action = action.lower()
        if action == "mute":
            pyautogui.press("volumemute")
            return "Audio output toggled mute, sir."
        elif action == "unmute":
            pyautogui.press("volumemute")
            return "Audio output unmuted, sir."
        elif action in ["up", "increase", "raise"]:
            for _ in range(5):
                pyautogui.press("volumeup")
            return "Master volume increased."
        elif action in ["down", "decrease", "lower"]:
            for _ in range(5):
                pyautogui.press("volumedown")
            return "Master volume decreased."
        elif action == "set" and level is not None:
            # Approximate volume set using keypresses
            for _ in range(50):
                pyautogui.press("volumedown")
            steps = int(level / 2)
            for _ in range(steps):
                pyautogui.press("volumeup")
            return f"Master volume calibrated to approximately {level} percent."
        return "Volume adjustment executed."

    def control_media(self, action: str) -> str:
        """Control media playback (Play, Pause, Next, Prev)."""
        action = action.lower()
        if action in ["play", "pause", "playpause", "toggle"]:
            pyautogui.press("playpause")
            return "Media playback toggled, sir."
        elif action in ["next", "skip"]:
            pyautogui.press("nexttrack")
            return "Skipping to next track."
        elif action in ["previous", "back", "prev"]:
            pyautogui.press("prevtrack")
            return "Returning to previous track."
        return "Media command sent."

    def take_screenshot(self) -> tuple[str, str]:
        """Capture screen and save timestamped image."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = SCREENSHOTS_DIR / filename
            
            screenshot = pyautogui.screenshot()
            screenshot.save(str(filepath))
            return str(filepath), f"Visual capture stored as {filename}, sir."
        except Exception as e:
            return "", f"Screenshot capture protocol encountered an error: {e}"

    def minimize_windows(self) -> str:
        """Minimize all open windows and show the desktop."""
        pyautogui.hotkey("win", "d")
        return "Desktop cleared, all windows minimized, sir."

    def lock_workstation(self) -> str:
        """Lock the Windows workstation immediately."""
        ctypes.windll.user32.LockWorkStation()
        return "Security protocols engaged. Workstation locked, sir."

    def web_search(self, query: str) -> str:
        """Open web search in default browser."""
        clean_query = query.strip()
        url = f"https://www.google.com/search?q={urllib.parse.quote(clean_query)}"
        webbrowser.open(url)
        return f"Browsing the web for '{clean_query}', sir."

    def youtube_search(self, query: str) -> str:
        """Search and play on YouTube."""
        clean_query = query.strip()
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(clean_query)}"
        webbrowser.open(url)
        return f"Streaming YouTube results for '{clean_query}', sir."

    def open_website(self, site_name: str) -> str:
        """Open common websites directly."""
        sites = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "github": "https://www.github.com",
            "gmail": "https://mail.google.com",
            "reddit": "https://www.reddit.com",
            "netflix": "https://www.netflix.com",
            "twitter": "https://www.twitter.com",
            "x": "https://www.x.com"
        }
        clean = site_name.lower().strip()
        target = sites.get(clean, f"https://{clean}.com")
        webbrowser.open(target)
        return f"Accessing {clean.title()}, sir."

    def get_time(self) -> str:
        """Get current formatted local time."""
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        return f"It is currently {time_str}, sir."

    def get_time_malayalam(self) -> str:
        """Get current local time formatted in natural Malayalam."""
        now = datetime.datetime.now()
        hour = now.hour
        minute = now.minute
        ampm = "രാവിലെ" if hour < 12 else ("ഉച്ചയ്ക്ക്" if hour < 16 else ("വൈകുന്നേരം" if hour < 20 else "രാത്രി"))
        h12 = hour % 12
        if h12 == 0:
            h12 = 12
        min_str = f" {minute} മിനിറ്റ്" if minute > 0 else ""
        return f"ഇപ്പോൾ സമയം {ampm} {h12} മണി{min_str} ആണ്, സാർ."

    def get_date(self) -> str:
        """Get current formatted local date."""
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        return f"Today is {date_str}, sir."

    def get_date_malayalam(self) -> str:
        """Get current local date formatted in natural Malayalam."""
        now = datetime.datetime.now()
        days = {
            "Monday": "തിങ്കളാഴ്ച",
            "Tuesday": "ചൊവ്വാഴ്ച",
            "Wednesday": "ബുധനാഴ്ച",
            "Thursday": "വ്യാഴാഴ്ച",
            "Friday": "വെള്ളിയാഴ്ച",
            "Saturday": "ശനിയാഴ്ച",
            "Sunday": "ഞായറാഴ്ച"
        }
        months = {
            1: "ജനുവരി", 2: "ഫെബ്രുവരി", 3: "മാർച്ച്", 4: "ഏപ്രിൽ",
            5: "മേയ്", 6: "ജൂൺ", 7: "ജൂലൈ", 8: "ഓഗസ്റ്റ്",
            9: "സെപ്റ്റംബർ", 10: "ഒക്ടോബർ", 11: "നവംബർ", 12: "ഡിസംബർ"
        }
        day_ml = days.get(now.strftime("%A"), "")
        month_ml = months.get(now.month, "")
        return f"ഇന്ന് {day_ml}, {now.year} {month_ml} {now.day} ആണ്, സാർ."

    def get_time_and_date(self) -> str:
        """Get current formatted local time and date."""
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d, %Y")
        return f"It is currently {time_str} on {date_str}, sir."


    def get_weather(self, city: str | None = None) -> str:
        """Fetch live weather summary via lightweight weather API."""
        try:
            target = city if city else ""
            url = f"https://wttr.in/{urllib.parse.quote(target)}?format=j1"
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                data = res.json()
                current = data["current_condition"][0]
                temp_c = current["temp_C"]
                desc = current["weatherDesc"][0]["value"]
                humidity = current["humidity"]
                wind = current["windspeedKmph"]
                location = city.title() if city else "your current sector"
                return f"Weather report for {location}: {desc}, {temp_c} degrees Celsius, with {humidity} percent humidity and winds at {wind} kilometers per hour."
        except Exception:
            pass
        return "Unable to access meteorological satellite data at this moment, sir."

system_controller = SystemController()
