# core/tts.py
# ASTRA text-to-speech engine
# Runs speech in a background thread so it never blocks the UI
# Signals back to character to set talking/idle mood

import threading
import pyttsx3
from PyQt6.QtCore import QObject, pyqtSignal


class TTSEngine(QObject):
    # emitted on main thread so character can update mood safely
    started  = pyqtSignal()   # ASTRA starts speaking → talking mood
    finished = pyqtSignal()   # ASTRA done speaking  → idle mood

    def __init__(self):
        super().__init__()
        self._engine  = None
        self._lock    = threading.Lock()
        self._speaking = False
        self._init_engine()

    def _init_engine(self):
        """Init pyttsx3 — called once. Safe to call again if engine crashes."""
        try:
            self._engine = pyttsx3.init()
            # voice settings — tweak these to taste
            self._engine.setProperty("rate",   175)   # words per minute
            self._engine.setProperty("volume", 0.9)   # 0.0 – 1.0
            # pick a female voice if available
            voices = self._engine.getProperty("voices")
            for v in voices:
                if "zira" in v.name.lower() or "female" in v.name.lower():
                    self._engine.setProperty("voice", v.id)
                    break
        except Exception as e:
            print(f"TTS init error: {e}")
            self._engine = None

    def speak(self, text: str):
        if self._speaking:
            return

        threading.Thread(
            target=self._speak_worker,
            args=(text,),
            daemon=True
        ).start()

    def _process_queue(self):
        while not self._queue.empty():
            text = self._queue.get()
            self._speak_worker(text)

    def speak_response(self, command: str):
        """
        Generate a short spoken response for a dispatched command.
        Call this after dispatch() so ASTRA confirms what she did.
        """
        responses = {
            "chrome":        "Opening Chrome.",
            "google chrome": "Opening Chrome.",
            "spotify":       "Opening Spotify.",
            "notepad":       "Opening Notepad.",
            "calculator":    "Opening Calculator.",
            "calc":          "Opening Calculator.",
            "vs code":       "Opening VS Code.",
            "vscode":        "Opening VS Code.",
            "explorer":      "Opening File Explorer.",
            "file explorer": "Opening File Explorer.",
            "task manager":  "Opening Task Manager.",
            "settings":      "Opening Settings.",
            "paint":         "Opening Paint.",
            "firefox":       "Opening Firefox.",
            "edge":          "Opening Edge.",
            "word":          "Opening Word.",
            "excel":         "Opening Excel.",
            "powerpoint":    "Opening PowerPoint.",
            "terminal":      "Opening Terminal.",
            "cmd":           "Opening Command Prompt.",
            "screenshot":    "Screenshot Saved"
        }
        # strip trigger words to find app name
        cmd = command.lower().strip()
        for trigger in ("open ", "launch ", "start ", "run "):
            if cmd.startswith(trigger):
                cmd = cmd[len(trigger):]
                break
        phrase = responses.get(cmd, f"Okay, running {cmd}.")
        self.speak(phrase)

    def _speak_worker(self, text: str):
        with self._lock:
            self._speaking = True
            self.started.emit()
            try:
                if self._engine is None:
                    self._init_engine()
                if self._engine:
                    self._engine.say(text)
                    self._engine.runAndWait()
            except Exception as e:
                print(f"TTS speak error: {e}")
                self._init_engine()   # re-init on crash
            finally:
                self._speaking = False
                self.finished.emit()

    def stop(self):
        """Interrupt current speech."""
        try:
            if self._engine:
                self._engine.stop()
        except:
            pass
