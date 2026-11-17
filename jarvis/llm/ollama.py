import http.client
import json
import socket
from contextlib import closing
from threading import Event, Thread
from urllib.parse import urlsplit

from jarvis.config import Settings
from jarvis.core.contracts import Message
from jarvis.core.process import Cancelled


class Ollama:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _request(self, path, payload=None, timeout=3, cancel=None):
        url = urlsplit(self.settings.ollama_url)
        with closing(http.client.HTTPConnection(url.hostname, url.port, timeout=timeout)) as connection:
            done = Event()
            watcher = None
            if cancel is not None:
                connection.connect()
                active_socket = connection.sock

                def watch():
                    while not done.wait(0.1):
                        if cancel.is_set():
                            try:
                                active_socket.shutdown(socket.SHUT_RDWR)
                            except OSError:
                                pass
                            return

                watcher = Thread(target=watch, name="jarvis-ollama-cancel", daemon=True)
                watcher.start()
            try:
                connection.request(
                    "GET" if payload is None else "POST", path,
                    body=None if payload is None else json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with connection.getresponse() as response:
                    if response.status != 200:
                        raise RuntimeError(f"Ollama devolvió HTTP {response.status}. Revisa el servicio y el modelo.")
                    return json.load(response)
            finally:
                done.set()
                if watcher is not None:
                    watcher.join()

    def model_available(self) -> bool:
        model = self.settings.model
        if ":" not in model.rsplit("/", 1)[-1]:
            model += ":latest"
        return any(item.get("name") == model for item in self._request("/api/tags")["models"])

    def reply(self, messages: list[Message], cancel: Event) -> str:
        if cancel.is_set():
            raise Cancelled()
        try:
            result = self._request("/api/chat", {
                "model": self.settings.model,
                "messages": messages,
                "stream": False,
                "think": False,
                "options": {"num_predict": self.settings.max_response_tokens},
            }, timeout=90, cancel=cancel)
        except (OSError, http.client.HTTPException, ValueError) as error:
            if cancel.is_set():
                raise Cancelled() from error
            raise RuntimeError(f"Falló la conexión o la inferencia de Ollama. {error}") from error
        if cancel.is_set():
            raise Cancelled()
        return result["message"]["content"].strip()
