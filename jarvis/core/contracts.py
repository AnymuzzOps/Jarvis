from pathlib import Path
from threading import Event
from typing import Protocol, TypedDict


class Message(TypedDict):
    role: str
    content: str


class LanguageModel(Protocol):
    def reply(self, messages: list[Message], cancel: Event) -> str: ...


class Transcriber(Protocol):
    def transcribe(self, wav: Path, cancel: Event) -> str: ...


class SpeechSynthesizer(Protocol):
    def synthesize(self, text: str, wav: Path, cancel: Event) -> None: ...
