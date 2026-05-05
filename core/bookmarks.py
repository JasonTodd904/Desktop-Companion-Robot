import webbrowser

BOOKMARKS = {
    "youtube": "https://www.youtube.com",
    "chat gpt": "https://chat.openai.com",
    "github": "https://github.com",
    "ai":   "https://claude.ai/new",
}

def open_bookmark(name):
    name = name.lower()

    for key in BOOKMARKS:
        if key in name:
            webbrowser.open(BOOKMARKS[key])
            print(f"Opened {key}")
            return True

    print(f"Bookmark not found: {name}")
    return False