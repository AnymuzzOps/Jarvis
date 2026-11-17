from concurrent.futures import ThreadPoolExecutor
from threading import Event

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from jarvis.audio import devices as audio
from jarvis.config import Settings
from jarvis.core.checks import check
from jarvis.core.session import Session, State
from jarvis.llm.ollama import Ollama
from jarvis.stt.whisper import Whisper
from jarvis.tts.piper import Piper
from jarvis.ui.settings_dialog import SettingsDialog
from jarvis.ui.visualizer import Visualizer


class Signals(QObject):
    status = Signal(object)
    message = Signal(str, str)
    error = Signal(str)
    level = Signal(float)
    recording_ready = Signal()
    completed = Signal(object)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JARVIS 1.0")
        self.resize(850, 720)
        self.setMinimumSize(520, 560)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="jarvis")
        self.cancel = Event()
        self.stop = Event()
        self.future = None
        self.closing = False
        self.recording = False
        self.mic_ready = False
        self.state = State.IDLE
        self.model_ready = False
        self.whisper_ready = False
        self.available_devices = []
        self.signals = Signals(self)
        self.session = Session(self.signals.status.emit, self.signals.message.emit, self.signals.error.emit)
        self.signals.status.connect(self.set_state)
        self.signals.message.connect(self.append_message)
        self.signals.error.connect(self.show_error)
        self.signals.level.connect(self.set_level)
        self.signals.recording_ready.connect(self.set_recording_ready)
        self.signals.completed.connect(self.finish_task, Qt.ConnectionType.QueuedConnection)
        self.build()
        try:
            self.settings = Settings.load()
        except (OSError, ValueError, TypeError, AttributeError) as error:
            self.settings = Settings()
            self.show_error(f"Configuración inválida. Se cargaron los valores predeterminados. {error}")
        self.refresh()

    def build(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 18, 24, 18)
        top = QHBoxLayout()
        title = QLabel("JARVIS")
        title.setObjectName("title")
        self.refresh_button = QPushButton("Verificar")
        self.refresh_button.clicked.connect(self.refresh)
        self.settings_button = QPushButton("Configuración")
        self.settings_button.clicked.connect(self.configure)
        top.addWidget(title, 1)
        top.addWidget(self.refresh_button)
        top.addWidget(self.settings_button)
        layout.addLayout(top)
        self.connection = QLabel()
        self.model = QLabel()
        self.assets = QLabel()
        for label in (self.connection, self.model, self.assets):
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            layout.addWidget(label)
        self.visualizer = Visualizer()
        layout.addWidget(self.visualizer)
        self.status = QLabel(State.IDLE.value)
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setObjectName("error")
        self.error_label.hide()
        layout.addWidget(self.error_label)
        self.conversation = QTextEdit()
        self.conversation.setAccessibleName("Conversación")
        self.conversation.setReadOnly(True)
        layout.addWidget(self.conversation, 1)
        composer = QHBoxLayout()
        self.microphone = QPushButton("Grabar")
        self.microphone.clicked.connect(self.toggle_microphone)
        self.entry = QLineEdit()
        self.entry.setAccessibleName("Mensaje")
        self.entry.setPlaceholderText("Escribe un mensaje")
        self.entry.setMaxLength(4000)
        self.entry.returnPressed.connect(self.send)
        self.entry.textChanged.connect(self.update_controls)
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self.send)
        composer.addWidget(self.microphone)
        composer.addWidget(self.entry, 1)
        composer.addWidget(self.send_button)
        layout.addLayout(composer)
        self.setStyleSheet("""
            QWidget { background: #091221; color: #d9edfa; font-size: 14px; }
            QLabel#title { color: #6cebff; font-size: 34px; font-weight: 700; }
            QLabel#status { color: #6cebff; font-weight: 700; }
            QLabel#error { color: #ff9d93; }
            QTextEdit, QLineEdit, QComboBox, QSpinBox {
                background: #101e30; border: 1px solid #2a4760; border-radius: 6px; padding: 8px;
            }
            QPushButton { background: #12334b; border: 1px solid #287096; border-radius: 6px; padding: 8px 12px; }
            QPushButton:hover { background: #1b4b68; }
            QPushButton:focus, QLineEdit:focus { border-color: #6cebff; }
            QPushButton:disabled { color: #7c92a3; background: #101e30; border-color: #2a4760; }
        """)
        self.update_controls()

    def run_task(self, fn):
        self.future = self.executor.submit(fn)
        self.future.add_done_callback(self.signals.completed.emit)
        self.update_controls()

    def finish_task(self, future):
        self.future = None
        self.recording = self.mic_ready = False
        if self.closing:
            self.close()
            return
        try:
            result = future.result()
        except Exception as error:
            self.set_state(State.ERROR)
            self.show_error(str(error))
        else:
            if result is not None:
                self.apply_checks(result)
        self.update_controls()

    def refresh(self):
        if self.future is not None:
            return
        self.connection.setText("Verificando Ollama…")
        settings = self.settings

        def inspect():
            checks = check(settings, Ollama(settings))
            try:
                available = audio.devices()
            except (OSError, audio.sd.PortAudioError) as error:
                return checks, [], str(error)
            return checks, available, ""

        self.run_task(inspect)

    def apply_checks(self, result):
        (connection, model, missing, self.model_ready, self.whisper_ready), self.available_devices, audio_error = result
        self.connection.setText(connection)
        self.model.setText(model)
        self.assets.setText("Falta: " + ", ".join(missing) if missing else "Whisper y Piper disponibles")
        if audio_error:
            self.show_error(f"No se pudieron enumerar los dispositivos de audio. {audio_error}")

    def configure(self):
        dialog = SettingsDialog(self.settings, self.available_devices, self)
        if dialog.exec():
            self.settings = dialog.settings
            self.error_label.hide()
            self.set_state(State.IDLE)
            self.refresh()

    def toggle_microphone(self):
        if self.recording:
            self.stop.set()
            self.update_controls()
        elif self.future is None and self.model_ready and self.whisper_ready:
            self.start_turn(None)

    def send(self):
        text = self.entry.text().strip()
        if text and self.future is None and self.model_ready:
            self.entry.clear()
            self.start_turn(text)

    def start_turn(self, text):
        self.error_label.hide()
        self.stop.clear()
        self.recording = text is None
        settings = self.settings
        self.run_task(lambda: self.session.run(
            settings, Ollama(settings), Whisper(settings), Piper(settings), audio, text,
            self.stop, self.cancel, self.signals.level.emit, self.signals.recording_ready.emit,
        ))

    def append_message(self, speaker, message):
        cursor = self.conversation.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if not self.conversation.document().isEmpty():
            cursor.insertBlock()
            cursor.insertBlock()
        cursor.insertText(f"{speaker}\n{message}")
        self.conversation.setTextCursor(cursor)
        self.conversation.ensureCursorVisible()

    def set_state(self, state):
        self.state = state
        self.status.setText(state.value)
        self.visualizer.state = state
        self.update_controls()

    def set_level(self, level):
        self.visualizer.level = level

    def set_recording_ready(self):
        self.mic_ready = True
        self.update_controls()

    def show_error(self, error):
        self.error_label.setText(error)
        self.error_label.setTextFormat(Qt.TextFormat.PlainText)
        self.error_label.show()

    def update_controls(self):
        idle = self.future is None and not self.closing
        listening = self.recording and self.state == State.LISTENING and self.mic_ready and not self.closing
        self.microphone.setText("Detener grabación" if self.recording else "Grabar")
        self.microphone.setEnabled((listening and not self.stop.is_set()) or (idle and self.model_ready and self.whisper_ready))
        self.send_button.setEnabled(idle and self.model_ready and bool(self.entry.text().strip()))
        self.settings_button.setEnabled(idle)
        self.refresh_button.setEnabled(idle)

    def closeEvent(self, event):
        if self.future is not None:
            event.ignore()
            self.closing = True
            self.cancel.set()
            self.stop.set()
            self.status.setText("Cerrando…")
            self.update_controls()
            return
        self.executor.shutdown(wait=False, cancel_futures=True)
        event.accept()
