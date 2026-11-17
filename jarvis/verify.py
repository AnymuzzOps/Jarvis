import json
import sys
from pathlib import Path
from threading import Event

from jarvis.config import Settings
from jarvis.core.checks import check
from jarvis.core.process import run_process
from jarvis.llm.ollama import Ollama


def main():
    try:
        settings = Settings.load()
    except (ValueError, OSError, TypeError, AttributeError) as error:
        print(f"Configuración inválida: {error}")
        return 1
    connection, model, missing, installed, _ = check(settings, Ollama(settings))
    print(connection)
    print(model)
    if missing:
        print("Falta: " + ", ".join(missing))
        return 1
    voice = Path(settings.voice)
    try:
        for asset in (Path(settings.whisper_model), voice):
            if asset.stat().st_size == 0:
                raise ValueError(f"Archivo vacío: {asset}")
        with voice.with_suffix(".onnx.json").open(encoding="utf-8") as config:
            if not json.load(config).get("audio", {}).get("sample_rate"):
                raise ValueError("La configuración de voz carece de audio.sample_rate.")
        for exe in (settings.whisper_exe, settings.piper_exe):
            run_process([exe, "--help"], Event(), timeout=20)
    except (ValueError, OSError, RuntimeError, AttributeError) as error:
        print(f"No se pudo validar Whisper o Piper: {error}")
        return 1
    print("Archivos y ejecutables de Whisper y Piper disponibles.")
    return int(not installed)


if __name__ == "__main__":
    sys.exit(main())
