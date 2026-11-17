import os
import subprocess
import time
from threading import Event


class Cancelled(Exception):
    """La aplicación solicitó detener el trabajo."""


def run_process(args: list[str], cancel: Event, timeout: int, input_data: bytes | None = None):
    if cancel.is_set():
        raise Cancelled()
    deadline = time.monotonic() + timeout
    with subprocess.Popen(
        args,
        stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONUTF8": "1"},
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    ) as process:
        try:
            while not cancel.is_set() and time.monotonic() < deadline:
                try:
                    _, error = process.communicate(input=input_data, timeout=0.2)
                except subprocess.TimeoutExpired:
                    input_data = None
                    continue
                if process.returncode:
                    detail = error.decode("utf-8", errors="replace").strip()[-600:]
                    raise RuntimeError(f"Proceso local terminó con código {process.returncode}. {detail}")
                return
            if cancel.is_set():
                raise Cancelled()
            raise TimeoutError("El proceso local superó el tiempo de espera.")
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
