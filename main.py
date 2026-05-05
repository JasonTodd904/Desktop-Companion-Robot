from ui.character import AstraCharacter, DemoControls
from core.dispatcher import dispatch
from PyQt6.QtWidgets import QApplication
import sys
import time   # ✅ ADD THIS

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(True)

astra = AstraCharacter()

def on_command(cmd):
    if "screenshot" in cmd:

        astra.force_hide_ui()

        QApplication.processEvents()
        time.sleep(0.3)

        result = dispatch(cmd)

        astra.force_show_ui()

        if result:
            astra.tts.speak("Screenshot saved")

    else:
        result = dispatch(cmd)

        if result:
            astra.tts.speak_response(cmd)

astra.command_ready.connect(on_command)
astra.show()

controls = DemoControls(astra)
controls.show()

sys.exit(app.exec())