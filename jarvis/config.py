import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit


def data_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Jarvis"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "jarvis"


@dataclass(frozen=True)
class Settings:
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "qwen3:4b"
    whisper_exe: str = str(data_dir() / "whisper" / "whisper-cli.exe")
    whisper_model: str = str(data_dir() / "models" / "ggml-base.bin")
    piper_exe: str = str(Path(sys.executable).with_name("piper.exe" if sys.platform == "win32" else "piper"))
    voice: str = str(data_dir() / "models" / "es_ES-sharvard-medium.onnx")
    input_device: int | None = None
    output_device: int | None = None
    max_record_seconds: int = 30
    max_response_tokens: int = 384
    language: str = "es"

    def __post_init__(self):
        url = urlsplit(self.ollama_url)
        if (url.scheme != "http" or url.hostname not in {"127.0.0.1", "::1"}
                or url.username is not None or url.password is not None
                or url.path not in ("", "/") or url.query or url.fragment):
            raise ValueError("Usa una URL HTTP de loopback, por ejemplo http://127.0.0.1:11434.")
        if url.port == 0:
            raise ValueError("El puerto de Ollama debe ser mayor que cero.")
        if not isinstance(self.model, str) or not self.model.strip() or self.language != "es":
            raise ValueError("Indica un modelo de Ollama y usa el idioma es.")
        if "cloud" in self.model.lower().replace("/", ":").replace("-", ":").split(":"):
            raise ValueError("Selecciona una variante local del modelo de Ollama.")
        if type(self.max_record_seconds) is not int or not 1 <= self.max_record_seconds <= 300:
            raise ValueError("La grabación debe durar entre 1 y 300 segundos.")
        if type(self.max_response_tokens) is not int or not 16 <= self.max_response_tokens <= 4096:
            raise ValueError("La respuesta debe tener un límite entre 16 y 4096 tokens.")
        for device in (self.input_device, self.output_device):
            if device is not None and (type(device) is not int or device < 0):
                raise ValueError("El identificador del dispositivo debe ser un entero positivo o cero.")

    @classmethod
    def load(cls, path: Path | None = None):
        path = path or data_dir() / "settings.json"
        if not path.exists():
            return cls()
        return cls(**json.loads(path.read_text(encoding="utf-8-sig")))

    def save(self, path: Path | None = None):
        path = path or data_dir() / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            name = Path(temporary.name)
            try:
                temporary.write(json.dumps(asdict(self), ensure_ascii=False, indent=2).encode("utf-8"))
                temporary.close()
                name.replace(path)
            finally:
                name.unlink(missing_ok=True)
