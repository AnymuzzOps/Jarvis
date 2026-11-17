import math

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from jarvis.core.session import State


class Visualizer(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(200)
        self.setAccessibleName("Visualizador de audio de JARVIS")
        self.state = State.IDLE
        self.level = 0.0
        self.amplitude = 0.0
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(33)

    def animate(self):
        self.angle = (self.angle + (1 if self.state == State.IDLE else 3)) % 360
        target = min(1.0, self.level * 4)
        self.amplitude += (target - self.amplitude) * 0.25
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        radius = min(cx, cy) * 0.68
        color = QColor("#ff887c" if self.state == State.ERROR else "#55e4ff")
        glow = QRadialGradient(cx, cy, radius * 1.5)
        glow.setColorAt(0, QColor("#143b58"))
        glow.setColorAt(1, QColor(10, 19, 33, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QPointF(cx, cy), radius * 1.5, radius * 1.5)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#1c5575"), 1))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)
        painter.drawEllipse(QPointF(cx, cy), radius * 0.72, radius * 0.72)
        painter.setPen(QPen(color, 2))
        canvas = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        for offset in (0, 180):
            painter.drawArc(canvas, (self.angle + offset) * 16, 58 * 16)
        for index in range(17):
            x = cx + (index - 8) * radius / 15
            weight = math.sin((index + 1) * math.pi / 18)
            height = 2 + radius * self.amplitude * weight * 0.65
            painter.drawLine(QPointF(x, cy - height), QPointF(x, cy + height))
