"""
Entry point with absolute imports so PyInstaller EXE runs cleanly.
Dev:  python -m src.main
EXE:  dist\InvisibleChat.exe
"""

from __future__ import annotations
import tkinter as tk

from src.gui import ChatGUI
from src.config import APP_TITLE


def main() -> None:
    root = tk.Tk()
    ChatGUI(root)
    root.title(APP_TITLE)
    root.mainloop()


if __name__ == "__main__":
    main()
