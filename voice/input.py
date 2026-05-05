import speech_recognition as sr

MIC_INDEX        = 1
AMBIENT_DURATION = 1.5

CONFIRM_WORDS = {"confirm", "okay", "ok", "correct", "right", "sure", "affirmative"}
CANCEL_WORDS  = {"cancel", "stop", "abort", "quit", "exit", "nevermind"}
RETRY_WORDS   = {"negative", "wrong", "repeat", "again", "retry", "redo", "nope"}

_recognizer = sr.Recognizer()
_calibrated  = False

def _calibrate():
    global _calibrated
    if _calibrated: return
    with sr.Microphone(device_index=MIC_INDEX) as source:
        _recognizer.adjust_for_ambient_noise(source, duration=AMBIENT_DURATION)
    _recognizer.pause_threshold  = 0.5
    _recognizer.phrase_threshold = 0.1
    _recognizer.energy_threshold = max(150, _recognizer.energy_threshold)
    _calibrated = True

def _capture(timeout=8, phrase_limit=10):
    with sr.Microphone(device_index=MIC_INDEX) as source:
        try:
            audio = _recognizer.listen(source, timeout=timeout,
                                       phrase_time_limit=phrase_limit)
        except sr.WaitTimeoutError:
            return None
    try:
        return _recognizer.recognize_google(audio).strip().lower()
    except:
        return None

def _confirm_loop(heard, on_status=None):
    while True:
        if on_status: on_status("confirming", heard)
        reply = _capture(timeout=8, phrase_limit=5)
        if reply is None: continue
        if any(w in reply for w in CONFIRM_WORDS): return "confirmed"
        if any(w in reply for w in CANCEL_WORDS):  return "cancelled"
        if any(w in reply for w in RETRY_WORDS):   return "retry"

def listen(confirm=True, on_status=None):
    """
    on_status(state, text) callback — called at each stage:
      on_status("listening", "")
      on_status("confirming", "open chrome")
      on_status("confirmed", "open chrome")
      on_status("cancelled", "")
      on_status("error", "")
    """
    _calibrate()
    while True:
        if on_status: on_status("listening", "")
        text = _capture(timeout=8, phrase_limit=10)
        if text is None:
            if on_status: on_status("error", "")
            continue
        if not confirm: return text
        outcome = _confirm_loop(text, on_status)
        if outcome == "confirmed":
            if on_status: on_status("confirmed", text)
            return text
        if outcome == "cancelled":
            if on_status: on_status("cancelled", "")
            return None
        # retry — loop back silently
