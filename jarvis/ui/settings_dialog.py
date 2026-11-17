from dataclasses import replace

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLineEdit, QMessageBox, QPushButton, QSpinBox, QWidget,
)


class SettingsDialog(QDialog):
    def __init__(self, settings, available, parent):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.resize(620, 0)
        self.settings = settings
        form = QFormLayout(self)
        self.fields = {}
        for key, label in {
            "ollama_url": "URL de Ollama", "model": "Modelo de lenguaje",
            "whisper_exe": "Ejecutable de Whisper", "whisper_model": "Modelo de Whisper",
            "piper_exe": "Ejecutable de Piper", "voice": "Voz de Piper (.onnx)",
        }.items():
            field = QLineEdit(getattr(settings, key))
            self.fields[key] = field
            if key in ("ollama_url", "model"):
                form.addRow(label, field)
                continue
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            browse = QPushButton("Elegir…")
            browse.clicked.connect(lambda checked=False, target=field: self.pick_file(target))
            row.addWidget(field)
            row.addWidget(browse)
            form.addRow(label, container)

        for key, label, channels in (
            ("input_device", "Micrófono", 2), ("output_device", "Altavoces", 3),
        ):
            field = QComboBox()
            field.addItem("Predeterminado del sistema", None)
            for device in available:
                if device[channels]:
                    field.addItem(f"{device[0]} · {device[1]}", device[0])
            selected = getattr(settings, key)
            if selected is not None and field.findData(selected) == -1:
                field.addItem(f"Dispositivo {selected} no disponible", selected)
            field.setCurrentIndex(max(0, field.findData(selected)))
            self.fields[key] = field
            form.addRow(label, field)

        for key, label, minimum, maximum in (
            ("max_record_seconds", "Grabación máxima (segundos)", 1, 300),
            ("max_response_tokens", "Respuesta máxima (tokens)", 16, 4096),
        ):
            field = QSpinBox()
            field.setRange(minimum, maximum)
            field.setValue(getattr(settings, key))
            self.fields[key] = field
            form.addRow(label, field)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def pick_file(self, field):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo", field.text())
        if path:
            field.setText(path)

    def accept(self):
        values = {}
        for key, field in self.fields.items():
            if isinstance(field, QLineEdit):
                values[key] = field.text().strip()
            elif isinstance(field, QSpinBox):
                values[key] = field.value()
            else:
                values[key] = field.currentData()
        try:
            updated = replace(self.settings, **values)
            updated.save()
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Configuración", str(error))
            return
        self.settings = updated
        super().accept()
