import os
import subprocess
import webbrowser
import time
import pyautogui
from core.browser import BrowserController
from core.bookmarks import open_bookmark
# ── APP REGISTRY ─────────────────────────────────────────────────────
# Add or change any app here.
# key   = word(s) you say
# value = path or command to launch
APP_MAP = {
    # browsers
    "chrome":        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":       r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge":          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",

    # media
    "spotify":       r"C:\Users\{USERNAME}\AppData\Roaming\Spotify\Spotify.exe",
    "vlc":           r"C:\Program Files\VideoLAN\VLC\vlc.exe",

    # productivity
    "notepad":       "notepad.exe",
    "notepad++":     r"C:\Program Files\Notepad++\notepad++.exe",
    "calculator":    "calc.exe",
    "calc":          "calc.exe",
    "paint":         "mspaint.exe",
    "word":          r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":         r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "powerpoint":    r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "vs code":       r"C:\Users\{USERNAME}\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vscode":        r"C:\Users\{USERNAME}\AppData\Local\Programs\Microsoft VS Code\Code.exe",

    # system
    "task manager":  "taskmgr.exe",
    "file explorer": "explorer.exe",
    "explorer":      "explorer.exe",
    "settings":      "ms-settings:",
    "control panel": "control",
    "cmd":           "cmd.exe",
    "terminal":      "wt.exe",          # Windows Terminal
}


def _resolve_path(path: str) -> str:
    """Replace {USERNAME} placeholder with actual Windows username."""
    return path.replace("{USERNAME}", os.environ.get("USERNAME", ""))


def _launch(path: str) -> bool:
    """
    Try to open a path/command.
    Uses os.startfile for known paths, subprocess for system commands.
    Returns True on success, False on failure.
    """
    path = _resolve_path(path)
    try:
        if path.startswith("ms-"):          # ms-settings: style URIs
            os.startfile(path)
        elif os.path.isfile(path):           # full .exe path
            os.startfile(path)
        else:                                # system command (notepad, calc…)
            subprocess.Popen(path, shell=True)
        return True
    except Exception as e:
        print(f"   ⚠️  Launch error: {e}")
        return False

def take_screenshot():
    try:
        # 🔥 CHANGE THIS PATH to your folder
        folder = r"C:\Users\KIIT0001\Pictures\Screenshots"

        # create folder if it doesn't exist
        os.makedirs(folder, exist_ok=True)

        # unique filename (no overwrite)
        filename = f"screenshot_{int(time.time())}.png"
        path = os.path.join(folder, filename)

        img = pyautogui.screenshot()
        img.save(path)

        print(f"📸 Saved at: {path}")
        return True

    except Exception as e:
        print(f"❌ Screenshot failed: {e}")
        return False

def search_google(cmd: str):
    try:
        query = cmd.replace("search", "").strip()
        if not query:
            print("   ❌ No search query provided")
            return False

        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        print(f"   🌐 Searching: {query}")
        return True
    except Exception as e:
        print(f"   ❌ Search failed: {e}")
        return False

def open_folder(cmd: str):
    try:
        if "downloads" in cmd:
            os.startfile(os.path.expanduser("~/Downloads"))

        elif "desktop" in cmd:
            os.startfile(os.path.expanduser("~/Desktop"))

        elif "documents" in cmd:
            os.startfile(os.path.expanduser("~/Documents"))

        else:
            print("Unknown folder")
            return False

        print("   📁 Folder opened")
        return True

    except Exception as e:
        print(f"   ❌ Folder open failed: {e}")
        return False


def dispatch(command: str) -> bool:
    """
    Main entry point. Takes confirmed command text, routes it to an action.
    Returns True if handled, False if unrecognised.

    Usage:
        from core.dispatcher import dispatch
        dispatch("open chrome")
    """
    cmd = command.lower().strip()
    print(f"\n📥 Dispatching: \"{cmd}\"")

    # ── OPEN / LAUNCH commands ───────────────────────────────────────
    # strip leading trigger words so "open chrome" → "chrome"
    trigger_words = ("open ", "launch ", "start ", "run ")
    app_name = cmd
    for trigger in trigger_words:
        if cmd.startswith(trigger):
            app_name = cmd[len(trigger):]
            break
    
        # ── SYSTEM / UTILITY COMMANDS ─────────────────────────────

    if "screenshot" in cmd or "take ss" in cmd:
        return take_screenshot()

    if cmd.startswith("search"):
        return search_google(cmd)

    if "open" in cmd and "folder" in cmd:
        return open_folder(cmd)

    if app_name in APP_MAP:
        path = APP_MAP[app_name]
        success = _launch(path)
        if success:
            print(f"   ✅ Opened: {app_name}")
        else:
            print(f"   ❌ Failed to open: {app_name} — check path in APP_MAP")
        return success

    from core.browser import BrowserController
from core.bookmarks import open_bookmark

browser = BrowserController()

def dispatch(cmd):
    cmd = cmd.lower()

    if cmd.startswith("bookmark "):
        name = cmd.replace("bookmark ", "")
        return open_bookmark(name)

    # 🔥 SEARCH (selenium)
    elif cmd.startswith("search "):
        query = cmd.replace("search ", "")
        browser.search_google(query)
        return True

    # 🔥 OPEN FIRST RESULT
    elif "open first" in cmd:
        return browser.open_first_result()
    
    elif "click images" in cmd:
         return browser.click_images()

    elif "scroll down" in cmd:
        return browser.scroll_down()

    elif "scroll up" in cmd:
        return browser.scroll_up()

    elif "click first image" in cmd:
        return browser.click_first_image()

    elif "open image" in cmd:
        return browser.open_image()

    return False


    # ── UNRECOGNISED ─────────────────────────────────────────────────
    print(f"   ❓ Unrecognised command: \"{cmd}\"")
    print(f"   💡 Tip: add it to APP_MAP in core/dispatcher.py")
    return False
