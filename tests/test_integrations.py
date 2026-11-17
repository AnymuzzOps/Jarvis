import http.client
import json
import socket
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Timer
from unittest import TestCase
from unittest.mock import patch

from jarvis.config import Settings
from jarvis.core.checks import check
from jarvis.core.process import Cancelled, run_process
from jarvis.llm.ollama import Ollama
from jarvis.stt.whisper import Whisper
from jarvis.tts.piper import Piper


class OllamaTests(TestCase):
    def test_chat_payload(self):
        ollama = Ollama(Settings())
        with patch.object(ollama, "_request", return_value={"message": {"content": " Hola "}}) as request:
            messages = [{"role": "user", "content": "Hola"}]
            self.assertEqual(ollama.reply(messages, Event()), "Hola")
        self.assertEqual(request.call_args.args[0], "/api/chat")
        payload = request.call_args.args[1]
        self.assertEqual(payload["messages"], messages)
        self.assertEqual(payload["options"]["num_predict"], 384)
        self.assertFalse(payload["think"])

    def test_http_transport_does_not_follow_redirects(self):
        with patch("jarvis.llm.ollama.http.client.HTTPConnection") as connection:
            response = connection.return_value.getresponse.return_value.__enter__.return_value
            response.status = 307
            with self.assertRaisesRegex(RuntimeError, "HTTP 307"):
                Ollama(Settings()).model_available()
            connection.assert_called_once_with("127.0.0.1", 11434, timeout=3)
            connection.return_value.close.assert_called_once()

    def test_close_interrupts_in_flight_inference(self):
        cancel = Event()
        released = Event()

        def blocked_response():
            if not released.wait(3):
                raise AssertionError("El socket no se cerró durante la inferencia")
            raise http.client.RemoteDisconnected()

        with patch("jarvis.llm.ollama.http.client.HTTPConnection") as connection:
            session = connection.return_value
            session.sock.shutdown.side_effect = lambda _: released.set()
            session.getresponse.side_effect = blocked_response
            timer = Timer(0.15, cancel.set)
            timer.start()
            try:
                with self.assertRaises(Cancelled):
                    Ollama(Settings()).reply([], cancel)
            finally:
                timer.cancel()
                timer.join()
            session.sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
            session.close.assert_called_once()

    def test_missing_models(self):
        with TemporaryDirectory() as directory:
            path = str(Path(directory) / "ausente")
            settings = replace(Settings(), whisper_exe=path, whisper_model=path, piper_exe=path, voice=path)
            ollama = Ollama(settings)
            with patch.object(ollama, "_request", return_value={"models": []}):
                connection, model, missing, installed, whisper = check(settings, ollama)
            self.assertIn("conectado", connection)
            self.assertIn("ollama pull qwen3:4b", model)
            self.assertIn("modelo Whisper", missing)
            self.assertFalse(installed)
            self.assertFalse(whisper)

    def test_invalid_or_remote_configuration(self):
        for url in ("http://example.com", "http://127.0.0.1@evil.example", "http://127.0.0.1/api"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                Settings(ollama_url=url)
        with self.assertRaises(ValueError):
            Settings(model="qwen3:4b-cloud")

    def test_config_roundtrip(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config" / "settings.json"
            settings = Settings(ollama_url="http://[::1]:11434", input_device=3, voice="voz española.onnx")
            settings.save(path)
            self.assertEqual(Settings.load(path), settings)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["language"], "es")


class ProviderTests(TestCase):
    def test_whisper_passes_spanish_and_reads_transcript(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "transcription.txt").write_text(" ¿Cómo estás?\n", encoding="utf-8")
            with patch("jarvis.stt.whisper.run_process") as run:
                self.assertEqual(Whisper(Settings()).transcribe(root / "input.wav", Event()), "¿Cómo estás?")
                args = run.call_args.args[0]
                self.assertEqual(args[args.index("-l") + 1], "es")

    def test_piper_passes_spanish_text_by_stdin(self):
        with patch("jarvis.tts.piper.run_process") as run:
            Piper(Settings()).synthesize("¿Cómo estás?", Path("salida.wav"), Event())
            self.assertEqual(run.call_args.kwargs["input_data"].decode("utf-8"), "¿Cómo estás?")
            self.assertIn("salida.wav", run.call_args.args[0])

    def test_process_transports_utf8_input_after_timeout_poll(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / "copy.txt"
            payload = "Español".encode()
            run_process([
                sys.executable, "-c",
                "import pathlib,sys,time; time.sleep(0.35); pathlib.Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())",
                str(target),
            ], Event(), timeout=4, input_data=payload)
            self.assertEqual(target.read_bytes(), payload)

    def test_close_terminates_child_process(self):
        cancel = Event()
        children = []

        def start(*args, **kwargs):
            child = popen(*args, **kwargs)
            children.append(child)
            cancel.set()
            return child

        popen = subprocess.Popen
        with patch("jarvis.core.process.subprocess.Popen", side_effect=start):
            with self.assertRaises(Cancelled):
                run_process([sys.executable, "-c", "import time; time.sleep(20)"], cancel, timeout=3)
        self.assertIsNotNone(children[0].poll())
