import sys
import math
import time
import random
import threading
import psutil
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QGridLayout
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (QPainter, QColor, QPen, QBrush,
                         QPainterPath, QLinearGradient, QRadialGradient, QCursor)
from ui.radial_menu import RadialMenu
from ui.speech_bubble import SpeechBubble
from voice.input import listen
from core.tts import TTSEngine

# ── PALETTE ────────────────────────────────────────────────────────
PALETTE = {
    "body":        QColor(220, 225, 230),
    "body_shadow": QColor(170, 180, 190),
    "body_shine":  QColor(255, 255, 255),
    "eye_bg":      QColor(10, 15, 25),
    "eye_glow":    QColor(80, 180, 255),
    "eye_shine":   QColor(200, 240, 255),
    "pupil":       QColor(255, 80, 125),
    "accent":      QColor(120, 200, 255),
    "screen_on":   QColor(100, 220, 255),
    "screen_off":  QColor(20, 30, 40),
}

MOODS = ["idle", "happy", "thinking", "listening",
         "surprised", "sleepy", "talking"]

MOOD_PRIORITY = {
    "idle":      0,
    "sleepy":    1,
    "thinking":  2,
    "talking":   3,
    "listening": 4,
    "happy":     0,
    "surprised": 0,
}

BATTERY_THRESHOLD = 30


class AstraCharacter(QWidget):
    mood_changed      = pyqtSignal(str)
    voice_mood_signal = pyqtSignal(str)
    command_ready     = pyqtSignal(str)
    _bubble_signal    = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(100, 120)

        self._env_mood         = "idle"
        self._voice_mood       = None
        self.mood              = "idle"
        self.blink             = 1.0
        self.blinking          = False
        self.head_bob          = 0.0
        self.head_tilt         = 0.0
        self._phase            = 0.0
        self.talk_phase        = 0.0
        self.brow_offset       = 0.0
        self.pupil_offset      = QPointF(0, 0)
        self._drag_pos         = None
        self.scale_factor      = 0.5
        self.eye_target        = QPointF(0, 0)
        self.eye_current       = QPointF(0, 0)
        self.glance_timer      = 0
        self.think_pause_timer = 0
        self.think_target      = QPointF(4, -4)
        self._voice_thread     = None
        self._last_hover_time  = time.time()

        self.menu   = RadialMenu(self)
        self.bubble = SpeechBubble(self)

        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.menu.hide_menu)

        # connect signals
        self.voice_mood_signal.connect(self._set_voice_mood)
        self._bubble_signal.connect(self._update_bubble)

        # TTS
        self.tts = TTSEngine()
        self.tts.started.connect(lambda: self._set_voice_mood("talking"))
        self.tts.finished.connect(lambda: self._set_voice_mood("idle"))

        # timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

        self._cursor_timer = QTimer(self)
        self._cursor_timer.timeout.connect(self._track_cursor)
        self._cursor_timer.start(50)

        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self._start_blink)
        self.blink_timer.start(3000)

        self._battery_timer = QTimer(self)
        self._battery_timer.timeout.connect(self._check_battery)
        self._battery_timer.start(60000)
        self._check_battery()

    # ── MOOD ───────────────────────────────────────────────────────
    def _resolve_mood(self):
        if self._voice_mood is not None:
            p_voice = MOOD_PRIORITY.get(self._voice_mood, 0)
            p_env   = MOOD_PRIORITY.get(self._env_mood,   0)
            self.mood = self._voice_mood if p_voice >= p_env else self._env_mood
        else:
            self.mood = self._env_mood
        self.update()

    def _set_voice_mood(self, mood: str):
        self._voice_mood = mood if mood != "idle" else None
        self._resolve_mood()

    def _set_env_mood(self, mood: str):
        self._env_mood = mood
        self._resolve_mood()

    def set_mood(self, mood: str):
        if mood in MOODS:
            self._env_mood = mood
            self._resolve_mood()

    # ── BATTERY ────────────────────────────────────────────────────
    def _check_battery(self):
        batt = psutil.sensors_battery()
        if batt is None: return
        if not batt.power_plugged and batt.percent <= BATTERY_THRESHOLD:
            if self._voice_mood is None:
                self._set_env_mood("sleepy")
        elif self._env_mood == "sleepy":
            self._set_env_mood("idle")

    # ── VOICE ──────────────────────────────────────────────────────
    def start_listening(self):
        if self._voice_thread and self._voice_thread.is_alive():
            return

        def _on_status(state, text):
            self._bubble_signal.emit(state, text)

        def _worker():
            try:
                self.voice_mood_signal.emit("listening")
                command = listen(confirm=True, on_status=_on_status)
                if command:
                    self.voice_mood_signal.emit("thinking")
                    self._bubble_signal.emit("executing", command)
                    time.sleep(0.5)
                    self.command_ready.emit(command)
                self.voice_mood_signal.emit("idle")
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.voice_mood_signal.emit("idle")

        self._voice_thread = threading.Thread(target=_worker, daemon=True)
        self._voice_thread.start()

    # ── BUBBLE ─────────────────────────────────────────────────────
    def _update_bubble(self, state: str, text: str):
        if   state == "listening":                self.bubble.show_listening()
        elif state == "confirming":               self.bubble.show_confirming(text)
        elif state in ("confirmed", "executing"): self.bubble.show_executing(text)
        elif state == "cancelled":                self.bubble.show_cancelled()
        elif state == "error":                    self.bubble.show_error()

    # ── ANIMATION ──────────────────────────────────────────────────
    def _tick(self):
        self._phase     += 0.05
        self.head_bob    = math.sin(self._phase * 1.2) * 5
        self.head_tilt   = math.sin(self._phase * 0.5) * 3
        self.brow_offset = math.sin(self._phase * 2)   * 1.5

        if self.mood == "talking":
            self.talk_phase += 0.3

        if self.mood == "thinking":
            self.think_pause_timer -= 1
            if self.think_pause_timer <= 0:
                self.think_target = QPointF(
                    4 + random.uniform(-1.5, 1.5),
                   -4 + random.uniform(-1.5, 1.5))
                self.think_pause_timer = random.randint(20, 60)
            self.eye_current.setX(
                self.eye_current.x() + (self.think_target.x() - self.eye_current.x()) * 0.05)
            self.eye_current.setY(
                self.eye_current.y() + (self.think_target.y() - self.eye_current.y()) * 0.05)

        if self.blinking:
            self.blink -= 0.2
            if self.blink <= 0:
                QTimer.singleShot(80, self._reopen)
                self.blinking = False
        else:
            self.blink = min(1.0, self.blink + 0.2)

        self.glance_timer -= 1
        if self.glance_timer <= 0 and self.mood == "idle":
            self.eye_target = QPointF(
                random.uniform(-5, 5),
                random.uniform(-4, 4))
            self.glance_timer = random.randint(60, 180)

        self.eye_current.setX(
            self.eye_current.x() + (self.eye_target.x() - self.eye_current.x()) * 0.1)
        self.eye_current.setY(
            self.eye_current.y() + (self.eye_target.y() - self.eye_current.y()) * 0.1)
        self.update()

    def _start_blink(self): self.blinking = True
    def _reopen(self):      self.blink = 0.0

    # ── CURSOR ─────────────────────────────────────────────────────
    def _track_cursor(self):
        if self.mood == "thinking":
            self.pupil_offset = QPointF(4, -4); return
        elif self.mood == "talking":
            self.pupil_offset = QPointF(0, 0);  return
        elif self.mood == "sleepy":
            self.pupil_offset = QPointF(0, 4);  return
        cur  = self.mapFromGlobal(QCursor.pos())
        cx   = self.width()  / 2
        cy   = self.height() * 0.38
        dx   = (cur.x() - cx) / self.width()
        dy   = (cur.y() - cy) / self.height()
        dist = math.hypot(dx, dy)
        if dist > 1: dx /= dist; dy /= dist
        self.pupil_offset = QPointF(dx * 6, dy * 6)

    # ── DRAG ───────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        self._last_hover_time = time.time()
        if not self.menu.visible:
            self.menu.show_menu()
        self.menu.update_positions()
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e): self._drag_pos = None

    def enterEvent(self, event):
        if getattr(self, "_ui_locked", False):
            return       
        self.hide_timer.stop()
        self.menu.show_menu()

    def leaveEvent(self, event):
        if getattr(self, "_ui_locked", False):
            return
        self.hide_timer.start(1500)

    def closeEvent(self, event):
        for btn in self.menu.buttons:
            btn.hide(); btn.deleteLater()
        event.accept()
        QApplication.instance().quit()

    # ── PAINT ──────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = self.scale_factor
        p.translate(self.width() / 2, self.height() / 2)
        p.scale(scale, scale)
        p.translate(-self.width() / 2, -self.height() / 2)
        w, h = self.width(), self.height()
        cx = w / 2
        self._draw_body(p, cx, h)
        p.save()
        p.translate(cx, h * 0.35 + self.head_bob)
        p.rotate(self.head_tilt)
        self._draw_head(p, 60)
        self._draw_eyes(p, 60)
        self._draw_mouth(p, 60)
        p.restore()

    def _draw_body(self, p, cx, h):
        bx = cx - 28
        by = h * 0.6
        grad = QLinearGradient(bx, by, bx + 56, by + 62)
        grad.setColorAt(0, PALETTE["body_shine"])
        grad.setColorAt(1, PALETTE["body_shadow"])
        p.setBrush(QBrush(grad))
        p.setPen(QPen(PALETTE["body_shadow"], 1))
        p.drawRoundedRect(QRectF(bx, by, 56, 62), 14, 14)

    def _draw_head(self, p, r):
        outer_rect = QRectF(-r * 1.1, -r * 0.8, r * 2.2, r * 1.6)
        outer_grad = QLinearGradient(outer_rect.topLeft(), outer_rect.bottomRight())
        outer_grad.setColorAt(0, PALETTE["body_shadow"])
        outer_grad.setColorAt(1, QColor(
            max(0, PALETTE["body_shadow"].red()   - 20),
            max(0, PALETTE["body_shadow"].green() - 20),
            max(0, PALETTE["body_shadow"].blue()  - 20)))
        p.setBrush(QBrush(outer_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(outer_rect, 22, 22)
        margin = 6
        inner_rect = QRectF(
            -r * 1.05 + margin, -r * 0.75 + margin,
             r * 2.1  - margin * 2, r * 1.5 - margin * 2)
        inner_grad = QLinearGradient(inner_rect.topLeft(), inner_rect.bottomRight())
        inner_grad.setColorAt(0, PALETTE["body_shine"])
        inner_grad.setColorAt(1, PALETTE["body"])
        p.setBrush(QBrush(inner_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(inner_rect, 16, 16)
        shine = QLinearGradient(inner_rect.topLeft(), inner_rect.bottomRight())
        shine.setColorAt(0,   QColor(255, 255, 255, 90))
        shine.setColorAt(0.3, QColor(255, 255, 255, 30))
        shine.setColorAt(1,   QColor(255, 255, 255,  0))
        p.setBrush(QBrush(shine))
        p.drawRoundedRect(inner_rect, 16, 16)
        p.setPen(QPen(QColor(180, 190, 200, 180), 1))
        p.drawLine(QPointF(-r + 12, -r + 16), QPointF(r - 12, -r + 16))

    def _draw_eyes(self, p, r):
        eye_y   = -r * 0.05
        eye_sep =  r * 0.5
        eye_r   =  r * 0.28
        for side in (-1, 1):
            ex = side * eye_sep
            self._draw_eye(p, ex, eye_y, eye_r)
            self._draw_eyebrow(p, ex, eye_y, eye_r, side)

    def _draw_eye(self, p, ex, ey, er):
        blink = self.blink
        if self.mood == "sleepy":
            eye_glow = QColor(80, 120, 160)
            eye_bg   = QColor(15, 20,  30)
        else:
            eye_glow = PALETTE["eye_glow"]
            eye_bg   = PALETTE["eye_bg"]
        visible_h = er * 2 * blink
        if visible_h < 2: return
        clip = QPainterPath()
        clip.addEllipse(QRectF(ex - er, ey - er, er * 2, visible_h))
        p.setClipPath(clip)
        p.setBrush(QBrush(eye_bg))
        p.setPen(QPen(PALETTE["accent"], 1.2))
        p.drawEllipse(QRectF(ex - er, ey - er, er * 2, er * 2))
        glow = QRadialGradient(ex, ey, er)
        glow.setColorAt(0.6,  QColor(0, 0, 0, 0))
        glow.setColorAt(0.85, QColor(80, 180, 255, 140))
        glow.setColorAt(1.0,  QColor(80, 180, 255, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(ex - er, ey - er, er * 2, er * 2))
        px = ex + self.pupil_offset.x()
        py = ey + self.pupil_offset.y()
        p.setBrush(QBrush(PALETTE["pupil"]))
        p.drawEllipse(QRectF(px - er * 0.35, py - er * 0.35, er * 0.7, er * 0.7))
        p.setBrush(QBrush(PALETTE["eye_shine"]))
        p.drawEllipse(QRectF(ex - er * 0.5, ey - er * 0.55, er * 0.3, er * 0.25))
        p.setClipping(False)
        lid_height = er * 0.6 * (1 - blink)
        p.setBrush(QBrush(PALETTE["body"]))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(ex - er, ey - er, er * 2, lid_height))
        if self.mood == "sleepy":
            p.drawRoundedRect(
                QRectF(ex - er, ey - er, er * 2, er * 0.9),
                er * 0.3, er * 0.3)
        raw_x = self.pupil_offset.x()
        raw_y = self.pupil_offset.y()
        iris_r = er * 0.6
        max_offset = er - iris_r - 2
        dist = math.hypot(raw_x, raw_y)
        if dist > max_offset:
            raw_x *= max_offset / dist
            raw_y *= max_offset / dist
        if self.mood == "sleepy":
            raw_y += er * 0.2

    def _draw_bar(self, p, ex, ey, er):
        p.setBrush(QBrush(PALETTE["eye_glow"]))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(ex-er*0.6, ey-er*0.15, er*1.2, er*0.3), 4, 4)

    def _draw_eyebrow(self, p, ex, ey, er, side):
        offset_y = ey - er * 1.2
        x1, x2 = ex - er * 0.6, ex + er * 0.6
        y1, y2 = offset_y, offset_y
        if self.mood == "happy":
            y1 -= er * 0.2; y2 -= er * 0.2
        elif self.mood == "thinking":
            if side == -1: y1 += er * 0.3; y2 -= er * 0.3
            else:          y1 -= er * 0.3; y2 += er * 0.3
        elif self.mood == "surprised":
            y1 -= er * 0.6; y2 -= er * 0.6
        elif self.mood == "sleepy":
            y1 += er * 0.3; y2 += er * 0.3
        p.setPen(QPen(QColor(120, 120, 130), 3,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_mouth(self, p, r):
        my = r * 0.35
        if self.mood == "happy":
            p.setPen(QPen(PALETTE["eye_glow"], 2))
            p.drawArc(QRectF(-20, my - 10, 40, 20), 0, -180 * 16)
        elif self.mood == "talking":
            height = 6 + abs(math.sin(self.talk_phase)) * 12
            p.setBrush(QBrush(QColor(20, 20, 25)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(-12, my, 24, height), 6, 6)
            p.setBrush(QBrush(QColor(230, 230, 230)))
            p.drawRect(QRectF(-12, my, 24, 4))
        elif self.mood == "thinking":
            p.setPen(QPen(PALETTE["eye_glow"], 2))
            p.drawLine(QPointF(-10, my + 4), QPointF(10, my - 4))
        elif self.mood == "sleepy":
            p.setPen(QPen(QColor(120, 120, 140), 2))
            p.drawLine(QPointF(-10, my), QPointF(10, my))
        else:
            p.setPen(QPen(PALETTE["eye_glow"], 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(-10, my - 4, 20, 10), 0, -180 * 16)
        p.setClipping(False)

    def update_mask(self):
        from PyQt6.QtGui import QRegion
        region  = QRegion()
        region += QRegion(40, 10,  100, 100, QRegion.RegionType.Ellipse)
        region += QRegion(60, 120, 60,  80)
        self.setMask(region)

    def hide_all(self):
        self.hide()

        if hasattr(self, "radial_menu"):
            self.radial_menu.hide()

        if hasattr(self, "speech_bubble"):
            self.speech_bubble.hide()
    
    def show_all(self):
        self.show()

        if hasattr(self, "radial_menu"):
            self.radial_menu.show()

        if hasattr(self, "speech_bubble"):
            self.speech_bubble.show()

    def force_hide_ui(self):
        self._ui_locked = True

        self.hide()

        # 🔥 hide radial menu buttons (REAL FIX)
        if hasattr(self, "menu") and self.menu:
            for btn in self.menu.buttons:
                btn.hide()

        # speech bubble
        if hasattr(self, "bubble") and self.bubble:
            self.bubble.hide()
    
    def force_show_ui(self):
        self._ui_locked = False

        self.show()



# ── CONTROLS ───────────────────────────────────────────────────────
class DemoControls(QWidget):
    def __init__(self, astra):
        super().__init__()
        self.astra = astra
        self.resize(200, 60)
        layout = QGridLayout(self)
        listen_btn = QPushButton("🎤 Listen")
        listen_btn.setMinimumSize(180, 44)
        listen_btn.clicked.connect(astra.start_listening)
        layout.addWidget(listen_btn, 0, 0)


# ── RUN ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    astra = AstraCharacter()
    astra.show()
    controls = DemoControls(astra)
    controls.show()
    sys.exit(app.exec())
