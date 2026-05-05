import math
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QPropertyAnimation


class RadialMenu:
    def __init__(self, parent):
        self.parent  = parent
        self.buttons = []
        self.visible = False
        self.radius  = 90

        # settings-only actions — no mood buttons
        self.actions = [
            ("🎤 listen",   "accent"),
            ("⚙ settings",  "normal"),
            ("🎨 theme",    "normal"),
            ("📌 pin",      "normal"),
            ("✕ close",    "danger"),
        ]
        self._create_buttons()

    def _create_buttons(self):
        for label, style in self.actions:
            btn = self._make_btn(label, style)

            if label == "🎤 listen":
                btn.clicked.connect(lambda: print("🎤 btn clicked"))
                btn.clicked.connect(self.parent.start_listening)
            elif label == "✕ close":
                btn.clicked.connect(self.parent.close)
            else:
                # placeholder — wire to settings panel later
                btn.clicked.connect(
                    lambda _, l=label: print(f"[menu] {l} — coming soon"))

            btn.enterEvent = lambda e: self.parent.hide_timer.stop()
            btn.leaveEvent = lambda e: self.parent.hide_timer.start(1500)
            self.buttons.append(btn)

    def _make_btn(self, label, style):
        btn = QPushButton(label)
        btn.setFixedSize(80, 28)
        btn.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool)
        btn.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        styles = {
            "normal": """
                QPushButton {
                    background: rgba(30,30,40,200);
                    color: #aaccff; border-radius:10px;
                    border:1px solid #445577; font-size:11px;
                }
                QPushButton:hover { background:rgba(60,60,90,220); color:white; }
            """,
            "accent": """
                QPushButton {
                    background: rgba(40,80,120,210);
                    color: #88ddff; border-radius:10px;
                    border:1px solid #5599cc; font-size:11px; font-weight:bold;
                }
                QPushButton:hover { background:rgba(60,120,180,230); color:white; }
            """,
            "danger": """
                QPushButton {
                    background: rgba(80,20,20,200);
                    color: #ff9988; border-radius:10px;
                    border:1px solid #884444; font-size:11px;
                }
                QPushButton:hover { background:rgba(120,30,30,220); color:white; }
            """,
        }
        btn.setStyleSheet(styles.get(style, styles["normal"]))
        btn.setWindowOpacity(0.0)
        return btn

    def update_positions(self):
        if not self.buttons: return
        pos   = self.parent.pos()
        cx    = pos.x() + self.parent.width()  / 2
        cy    = pos.y() + self.parent.height() / 2
        count = len(self.buttons)
        for i, btn in enumerate(self.buttons):
            angle = (2 * math.pi / count) * i - math.pi / 2
            x = cx + self.radius * math.cos(angle) - btn.width()  / 2
            y = cy + self.radius * math.sin(angle) - btn.height() / 2
            btn.move(int(x), int(y))

    def show_menu(self):
        if self.visible: return
        self.visible = True
        self.update_positions()
        for btn in self.buttons:
            btn.show(); btn.raise_()
            anim = QPropertyAnimation(btn, b"windowOpacity")
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.start()
            btn._anim = anim

    def hide_menu(self):
        if not self.visible: return
        self.visible = False
        for btn in self.buttons:
            anim = QPropertyAnimation(btn, b"windowOpacity")
            anim.setDuration(200)
            anim.setStartValue(btn.windowOpacity())
            anim.setEndValue(0.0)
            anim.finished.connect((lambda b=btn: b.hide()))
            anim.start()
            btn._anim = anim
