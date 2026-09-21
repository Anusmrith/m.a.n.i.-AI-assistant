import json
import datetime
from pathlib import Path
from jarvis.config import NOTES_FILE

class NotesManager:
    def __init__(self):
        self.file_path = NOTES_FILE
        self._ensure_file()

    def _ensure_file(self):
        if not self.file_path.exists():
            self.file_path.write_text("[]", encoding="utf-8")

    def _read(self) -> list[dict]:
        try:
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _write(self, notes: list[dict]):
        self.file_path.write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_note(self, content: str) -> dict:
        notes = self._read()
        note = {
            "id": len(notes) + 1,
            "text": content.strip(),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        notes.append(note)
        self._write(notes)
        return note

    def list_notes(self) -> list[dict]:
        return self._read()

    def clear_notes(self) -> int:
        notes = self._read()
        count = len(notes)
        self._write([])
        return count

    def get_voice_summary(self) -> str:
        notes = self.list_notes()
        if not notes:
            return "You have no active notes in the database, sir."
        summary = [f"You have {len(notes)} saved notes, sir:"]
        for idx, n in enumerate(notes, start=1):
            summary.append(f"Note {idx}: {n['text']}.")
        return " ".join(summary)

notes_manager = NotesManager()
