from http.client import HTTPException
from pathlib import Path

from jarvis.config import Settings
from jarvis.llm.ollama import Ollama


def check(settings: Settings, ollama: Ollama):
    try:
        installed = ollama.model_available()
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, HTTPException) as error:
        connected = False
        installed = False
        connection = f"Ollama no disponible. Abre Ollama y revisa la URL. {error}"
    else:
        connected = True
        connection = "Ollama conectado"

    voice = Path(settings.voice)
    assets = {
        "whisper-cli": Path(settings.whisper_exe),
        "modelo Whisper": Path(settings.whisper_model),
        "Piper": Path(settings.piper_exe),
        "voz Piper": voice,
        "configuración de voz": voice.with_suffix(".onnx.json"),
    }
    missing = [label for label, path in assets.items() if not path.is_file()]
    model = f"{settings.model} disponible" if installed else f"{settings.model} sin verificar"
    if connected and not installed:
        model = f"Falta {settings.model}. Ejecuta ollama pull {settings.model}"
    return connection, model, missing, installed, not any(label in missing for label in ("whisper-cli", "modelo Whisper"))
