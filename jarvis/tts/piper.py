from pathlib import Path
from threading import Event

from jarvis.config import Settings
from jarvis.core.process import run_process


class Piper:
    def __init__(self, settings: Settings):
        self.settings = settings

    def synthesize(self, text: str, wav: Path, cancel: Event):
        run_process([
            self.settings.piper_exe, "-m", self.settings.voice, "-f", str(wav),
        ], cancel, timeout=90, input_data=text.encode("utf-8"))
