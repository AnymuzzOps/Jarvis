from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from threading import Event
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

import numpy as np


class AudioTests(TestCase):
    def setUp(self):
        self.sd = MagicMock()
        self.sf = MagicMock()
        path = Path(__file__).resolve().parents[1] / "jarvis/audio/devices.py"
        spec = spec_from_file_location("jarvis_test_audio", path)
        self.audio = module_from_spec(spec)
        with patch.dict("sys.modules", {"sounddevice": self.sd, "soundfile": self.sf}):
            spec.loader.exec_module(self.audio)

    def test_play_streams_samples_and_reports_signal(self):
        stream = self.sd.OutputStream.return_value.__enter__.return_value
        stream.write.return_value = False
        wav = self.sf.SoundFile.return_value.__enter__.return_value
        wav.frames, wav.samplerate, wav.channels = 320, 16000, 1
        block = np.full((320, 1), 0.5, dtype="float32")
        wav.blocks.return_value = [block]
        level = Mock()
        self.audio.play(Path("response.wav"), 3, Event(), level)
        self.sd.OutputStream.assert_called_once_with(device=3, samplerate=16000, channels=1, dtype="float32")
        stream.write.assert_called_once_with(block)
        level.assert_called_once_with(0.5)
        self.sd.OutputStream.return_value.__exit__.assert_called_once()

    def test_canceled_playback_aborts_stream(self):
        stream = self.sd.OutputStream.return_value.__enter__.return_value
        wav = self.sf.SoundFile.return_value.__enter__.return_value
        wav.frames, wav.samplerate, wav.channels = 320, 16000, 1
        wav.blocks.return_value = [np.zeros((320, 1), dtype="float32")]
        cancel = Event()
        cancel.set()
        self.audio.play(Path("response.wav"), None, cancel, Mock())
        stream.abort.assert_called_once()
        stream.write.assert_not_called()

    def test_recording_device_failure_releases_stream(self):
        stream = self.sd.InputStream.return_value.__enter__.return_value
        stream.read.return_value = (np.zeros((320, 1), dtype="int16"), True)
        with self.assertRaisesRegex(RuntimeError, "perdieron muestras"):
            self.audio.record(Path("test.wav"), None, 1, Event(), Event(), Mock(), Mock())
        self.sd.InputStream.return_value.__exit__.assert_called_once()

    def test_silent_recording_produces_no_wav(self):
        stream = self.sd.InputStream.return_value.__enter__.return_value
        stream.read.return_value = (np.zeros((320, 1), dtype="int16"), False)
        self.assertFalse(self.audio.record(Path("test.wav"), None, 1, Event(), Event(), Mock(), Mock()))
        self.sf.write.assert_not_called()
