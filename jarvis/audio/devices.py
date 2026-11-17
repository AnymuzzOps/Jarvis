from pathlib import Path
from threading import Event

import numpy as np
import sounddevice as sd
import soundfile as sf


def devices():
    return [
        (index, device["name"], device["max_input_channels"], device["max_output_channels"])
        for index, device in enumerate(sd.query_devices())
    ]


def record(path: Path, device, seconds: int, stop: Event, cancel: Event, level, ready):
    rate = 16000
    block_size = 320
    frames = []
    with sd.InputStream(device=device, samplerate=rate, channels=1, dtype="int16", blocksize=block_size) as stream:
        ready()
        for _ in range(seconds * rate // block_size):
            if stop.is_set() or cancel.is_set():
                break
            block, overflow = stream.read(block_size)
            if overflow:
                raise RuntimeError("Se perdieron muestras del micrófono. Intenta grabar otra vez.")
            frames.append(block)
            level(float(np.sqrt(np.mean((block.astype(np.float32) / 32768) ** 2))))
    if not frames or cancel.is_set():
        return False
    samples = np.concatenate(frames)
    if len(samples) < rate // 5 or not np.any(samples):
        return False
    sf.write(path, samples, rate, subtype="PCM_16")
    return True


def play(path: Path, device, cancel: Event, level):
    with sf.SoundFile(path) as wav:
        if wav.frames == 0:
            raise RuntimeError("Piper produjo un archivo de voz vacío.")
        with sd.OutputStream(device=device, samplerate=wav.samplerate, channels=wav.channels,
                             dtype="float32") as stream:
            for block in wav.blocks(blocksize=max(1, wav.samplerate // 50), dtype="float32", always_2d=True):
                if cancel.is_set():
                    stream.abort()
                    break
                if stream.write(block):
                    raise RuntimeError("Se interrumpió la reproducción de voz. Revisa el dispositivo de salida.")
                level(float(np.sqrt(np.mean(block ** 2))))
