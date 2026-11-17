from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest import TestCase
from unittest.mock import Mock

from jarvis.config import Settings
from jarvis.core.session import Session, State


class SessionTests(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        root = Path(directory)
        voice = root / "voice.onnx"
        piper = root / "piper.exe"
        for file in (voice, voice.with_suffix(".onnx.json"), piper):
            file.touch()
        self.settings = replace(Settings(), voice=str(voice), piper_exe=str(piper))
        self.states = []
        self.messages = []
        self.errors = []
        self.session = Session(self.states.append, lambda *message: self.messages.append(message), self.errors.append)
        self.llm = Mock()
        self.llm.reply.return_value = "Una respuesta"
        self.stt = Mock()
        self.stt.transcribe.return_value = "Buenos días"
        self.audio = Mock()
        self.audio.record.return_value = True
        self.tts = Mock()
        self.cancel = Event()

    def turn(self, text=None):
        self.session.run(self.settings, self.llm, self.stt, self.tts, self.audio, text,
                         Event(), self.cancel, Mock(), Mock())

    def test_voice_turn_and_temporary_cleanup(self):
        self.turn()
        self.assertEqual(self.states, [State.LISTENING, State.TRANSCRIBING, State.THINKING, State.SPEAKING, State.IDLE])
        self.assertEqual(self.messages, [("Tú", "Buenos días"), ("JARVIS", "Una respuesta")])
        audio_path = self.audio.play.call_args.args[0]
        self.assertEqual(audio_path, self.tts.synthesize.call_args.args[1])
        self.assertFalse(audio_path.parent.exists())

    def test_text_keeps_recent_complete_turns(self):
        for index in range(8):
            self.turn(f"Texto {index}")
        messages = self.llm.reply.call_args.args[0]
        self.assertEqual(len(messages), 14)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["content"], "Texto 1")
        self.assertEqual(messages[-1]["content"], "Texto 7")
        self.audio.record.assert_not_called()
        self.stt.transcribe.assert_not_called()

    def test_empty_recording(self):
        self.audio.record.return_value = False
        self.turn()
        self.assertEqual(self.states, [State.LISTENING, State.ERROR])
        self.assertIn("Grabación vacía", self.errors[0])
        self.llm.reply.assert_not_called()

    def test_device_failure_then_recovery(self):
        self.audio.record.side_effect = RuntimeError("No hay micrófono")
        self.turn()
        self.assertEqual(self.errors, ["No hay micrófono"])
        self.turn("Hola")
        self.assertEqual(self.states[-1], State.IDLE)

    def test_inference_failure_does_not_commit_context(self):
        self.llm.reply.side_effect = RuntimeError("Error de inferencia")
        self.turn("Primer mensaje")
        self.assertEqual(self.states[-1], State.ERROR)
        self.assertFalse(self.session.history)
        self.audio.play.assert_not_called()

    def test_missing_voice_leaves_generated_text_visible(self):
        Path(self.settings.voice).unlink()
        self.turn("Hola")
        self.assertEqual(self.states[-1], State.ERROR)
        self.assertIn("Falta Piper", self.errors[0])
        self.assertEqual(self.messages[-1], ("JARVIS", "Una respuesta"))

    def test_playback_error_keeps_generated_answer_in_context(self):
        self.audio.play.side_effect = RuntimeError("Salida desconectada")
        self.turn("Hola")
        self.assertEqual(self.errors, ["Salida desconectada"])
        self.assertEqual(self.session.history[-1]["content"], "Una respuesta")

    def test_shutdown_during_recording_stops_pipeline(self):
        def cancel_recording(*args):
            self.cancel.set()
            return False

        self.audio.record.side_effect = cancel_recording
        self.turn()
        self.assertEqual(self.states[-1], State.IDLE)
        self.assertEqual(self.errors, [])
        self.stt.transcribe.assert_not_called()
