# ui/speech_bubble.py
# Floating speech bubble that appears near ASTRA
# showing voice status, heard text, and confirmation prompt

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint
from PyQt6.QtGui import (QPainter, QColor, QPen, QBrush,
                         QPainterPath, QFont)

# bubble colors per state
STATE_COLORS = {
    "listening":   ("#5599cc", "listening..."),
    "confirming":  ("#aa88ff", "did you mean?"),
    "executing":   ("#55cc88", "executing..."),
    "cancelled":   ("#cc6655", "cancelled"),
    "error":       ("#cc5544", "not understood"),
}

BUBBLE_W = 240
BUBBLE_H = 90
TAIL_H   = 14   # height of the pointy tail


class SpeechBubble(QWidget):
    def __init__(self, parent_widget):
        super().__init__()
        self.parent_widget = parent_widget   # AstraCharacter
        self._state        = "listening"
        self._heard        = ""
        self._prompt       = ""

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(BUBBLE_W, BUBBLE_H + TAIL_H)

        # auto-hide timer (used after executing/cancelled)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

    # ── PUBLIC API ─────────────────────────────────────────────────
    def show_listening(self):
        self._state  = "listening"
        self._heard  = ""
        self._prompt = ""
        self._hide_timer.stop()
        self._reposition()
        self._fade_in()

    def show_confirming(self, heard: str):
        self._state  = "confirming"
        self._heard  = heard
        self._prompt = "say confirm / cancel / negative"
        self._hide_timer.stop()
        self._reposition()
        self.update()

    def show_executing(self, command: str):
        self._state  = "executing"
        self._heard  = command
        self._prompt = ""
        self._reposition()
        self.update()
        self._hide_timer.start(2000)   # auto-hide after 2s

    def show_cancelled(self):
        self._state  = "cancelled"
        self._heard  = ""
        self._prompt = ""
        self._reposition()
        self.update()
        self._hide_timer.start(1500)   # auto-hide after 1.5s

    def show_error(self):
        self._state  = "error"
        self._heard  = ""
        self._prompt = ""
        self._reposition()
        self.update()
        self._hide_timer.start(2000)

    # ── POSITION ───────────────────────────────────────────────────
    def _reposition(self):
        """Place bubble above and to the left of ASTRA."""
        pos = self.parent_widget.pos()
        x   = pos.x() - BUBBLE_W + self.parent_widget.width()
        y   = pos.y() - BUBBLE_H - TAIL_H - 8
        # keep on screen
        screen = self.screen().availableGeometry()
        x = max(4, min(x, screen.width()  - BUBBLE_W - 4))
        y = max(4, min(y, screen.height() - BUBBLE_H - TAIL_H - 4))
        self.move(x, y)

    # ── FADE ───────────────────────────────────────────────────────
    def _fade_in(self):
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start()
        self._anim = anim

    def _fade_out(self):
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.finished.connect(self.hide)
        anim.start()
        self._anim = anim

    # ── PAINT ──────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        color_hex, status_text = STATE_COLORS.get(
            self._state, ("#5599cc", "..."))
        dot_color = QColor(color_hex)

        # ── bubble body ──
        body = QPainterPath()
        body.addRoundedRect(0, 0, BUBBLE_W, BUBBLE_H, 14, 14)
        p.setBrush(QBrush(QColor(22, 22, 32, 230)))
        p.setPen(QPen(QColor(60, 70, 100, 180), 1))
        p.drawPath(body)

        # ── tail (pointing down toward ASTRA) ──
        tail = QPainterPath()
        tail_x = BUBBLE_W - 40
        tail.moveTo(tail_x, BUBBLE_H)
        tail.lineTo(tail_x + 12, BUBBLE_H + TAIL_H)
        tail.lineTo(tail_x + 24, BUBBLE_H)
        tail.closeSubpath()
        p.setBrush(QBrush(QColor(22, 22, 32, 230)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(tail)

        # ── status dot + label ──
        p.setBrush(QBrush(dot_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(14, 14, 8, 8)

        f = QFont(); f.setPointSize(9); f.setFamily("Segoe UI")
        p.setFont(f)
        p.setPen(QPen(QColor(color_hex)))
        p.drawText(28, 23, status_text)

        # ── divider ──
        p.setPen(QPen(QColor(60, 70, 100, 120), 1))
        p.drawLine(12, 32, BUBBLE_W - 12, 32)

        # ── heard text ──
        if self._heard:
            f2 = QFont(); f2.setPointSize(9); f2.setFamily("Segoe UI")
            p.setFont(f2)
            p.setPen(QPen(QColor(160, 170, 180)))
            p.drawText(14, 48, "heard")
            f3 = QFont(); f3.setPointSize(10)
            f3.setFamily("Segoe UI"); f3.setBold(True)
            p.setFont(f3)
            p.setPen(QPen(QColor(220, 230, 245)))
            # truncate if too long
            heard = self._heard if len(self._heard) <= 24 else self._heard[:22] + "…"
            p.drawText(62, 48, f'"{heard}"')

        # ── prompt text ──
        if self._prompt:
            f4 = QFont(); f4.setPointSize(8); f4.setFamily("Segoe UI")
            p.setFont(f4)
            p.setPen(QPen(QColor(120, 130, 150)))
            p.drawText(14, 68, self._prompt)


# ── BUBBLE SIGNAL BRIDGE ───────────────────────────────────────────
# Connects voice_input callbacks to bubble UI updates.
# Import and call setup_bubble() from main.py
def setup_bubble(astra, bubble):
    """Wire bubble signals into voice pipeline via astra signals."""

    # reposition bubble when ASTRA moves
    original_move = astra.moveEvent
    def on_move(event):
        if bubble.isVisible():
            bubble._reposition()
        if original_move:
            original_move(event)
    astra.moveEvent = on_move
