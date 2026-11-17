from pathlib import Path
from threading import Event

from jarvis.config import Settings
from jarvis.core.process import run_process


class Whisper:
    def __init__(self, settings: Settings):
        self.settings = settings

    def transcribe(self, wav: Path, cancel: Event) -> str:
        output = wav.parent / "transcription"
        run_process([
            self.settings.whisper_exe, "-m", self.settings.whisper_model,
            "-f", str(wav), "-l", self.settings.language, "-otxt", "-of", str(output),
        ], cancel, timeout=120)
        return output.with_suffix(".txt").read_text(encoding="utf-8").strip()
