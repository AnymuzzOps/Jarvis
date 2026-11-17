from collections import deque
from enum import StrEnum
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event

from jarvis.config import Settings
from jarvis.core.contracts import LanguageModel, Message, SpeechSynthesizer, Transcriber
from jarvis.core.process import Cancelled


class State(StrEnum):
    IDLE = "INACTIVO"
    LISTENING = "ESCUCHANDO"
    TRANSCRIBING = "TRANSCRIBIENDO"
    THINKING = "PROCESANDO"
    SPEAKING = "HABLANDO"
    ERROR = "ERROR"


PERSONALITY = (
    "Eres JARVIS, un asistente de conversación local. Habla en español natural, con claridad, "
    "profesionalidad y cordialidad. Usa humor sutil cuando encaje y evita frases repetitivas. "
    "No afirmes que puedes controlar aplicaciones, acceder a internet o ejecutar acciones. "
    "Responde con texto apto para leer en voz alta."
)


class Session:
    def __init__(self, status, message, error):
        self.history = deque(maxlen=12)
        self.status = status
        self.message = message
        self.error = error

    def run(self, settings: Settings, llm: LanguageModel, stt: Transcriber, tts: SpeechSynthesizer,
            audio, text: str | None, stop: Event, cancel: Event, level, ready):
        try:
            with TemporaryDirectory(prefix="jarvis-") as directory:
                folder = Path(directory)
                if text is None:
                    self.status(State.LISTENING)
                    recording = folder / "input.wav"
                    recorded = audio.record(recording, settings.input_device, settings.max_record_seconds,
                                            stop, cancel, level, ready)
                    if cancel.is_set():
                        raise Cancelled()
                    if not recorded:
                        raise ValueError("Grabación vacía o demasiado corta. Intenta de nuevo.")
                    level(0.0)
                    self.status(State.TRANSCRIBING)
                    text = stt.transcribe(recording, cancel)
                    if not text.strip():
                        raise ValueError("No se reconoció voz. Revisa el micrófono e intenta de nuevo.")

                if cancel.is_set():
                    raise Cancelled()
                user: Message = {"role": "user", "content": text}
                self.message("Tú", text)
                self.status(State.THINKING)
                answer = llm.reply([{"role": "system", "content": PERSONALITY}, *self.history, user], cancel)
                if not answer.strip():
                    raise ValueError("Ollama devolvió una respuesta vacía.")
                self.history.extend((user, {"role": "assistant", "content": answer}))
                self.message("JARVIS", answer)

                voice = Path(settings.voice)
                if not all(path.is_file() for path in (Path(settings.piper_exe), voice, voice.with_suffix(".onnx.json"))):
                    raise FileNotFoundError("Falta Piper, la voz o su archivo .onnx.json. Revisa Configuración.")
                self.status(State.SPEAKING)
                speech = folder / "reply.wav"
                tts.synthesize(answer, speech, cancel)
                audio.play(speech, settings.output_device, cancel, level)
        except Cancelled:
            pass
        except Exception as error:
            if not cancel.is_set():
                self.status(State.ERROR)
                self.error(str(error))
                return
        finally:
            level(0.0)
        self.status(State.IDLE)
