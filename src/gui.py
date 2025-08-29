"""
Tkinter GUI:
- Solid, dark theme (clearly visible)
- Status badge showing which capture exclusion applied
- Ctrl+Alt+I to hide/show
- Async calls with logging
"""

from __future__ import annotations

import asyncio
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
from typing import Callable, Optional

from .api_client import GrokAPIClient, ChatAPIError
from .config import APP_TITLE, DEFAULT_ALPHA
from .utils import get_api_key, save_api_key, set_window_excluded_from_capture, logger


class AsyncioRunner:
    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run_coro(self, coro, callback=None, errback=None) -> None:
        async def wrapper():
            return await coro
        fut = asyncio.run_coroutine_threadsafe(wrapper(), self._loop)

        def done(f):
            try:
                res = f.result()
                if callback:
                    callback(res)
            except Exception as e:
                if errback:
                    errback(e)
        fut.add_done_callback(done)

    def stop(self) -> None:
        try:
            self._loop.call_soon_threadsafe(self._loop.stop)
        except Exception:
            pass


class ChatGUI:
    def __init__(self, root: tk.Tk, on_ready: Optional[Callable[[], None]] = None) -> None:
        self.root = root
        self.on_ready = on_ready
        self._hidden = False
        self.runner = AsyncioRunner()

        # Window
        self.root.title(APP_TITLE)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", DEFAULT_ALPHA)
        self.root.geometry("860x600")
        self.root.minsize(580, 380)

        # Colors
        bg = "#1e1e1e"; fg = "#e6e6e6"; panel = "#252526"; accent = "#0e639c"
        self.root.configure(bg=bg)

        # Status bar (shows exclusion state)
        self.status_var = tk.StringVar(value="Capture: …")
        status = tk.Label(self.root, textvariable=self.status_var, anchor="w",
                          bg=bg, fg="#9cdcfe", padx=8)
        status.pack(fill=tk.X)

        # Chat area
        self.chat_display = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, state=tk.DISABLED,
            bg=panel, fg=fg, insertbackground=fg, bd=0, relief=tk.FLAT
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 4))

        # Input row
        row = tk.Frame(self.root, bg=bg, bd=0)
        row.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(row, textvariable=self.input_var,
                                    bg=panel, fg=fg, insertbackground=fg,
                                    bd=0, relief=tk.FLAT)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self.input_entry.bind("<Return>", self._on_return)

        self.send_btn = tk.Button(row, text="Send", bg=accent, fg="white",
                                  activebackground="#1177bb", activeforeground="white",
                                  bd=0, relief=tk.FLAT, padx=14, pady=6,
                                  command=self.handle_send)
        self.send_btn.pack(side=tk.LEFT, padx=(8, 0))

        # Toggle hotkey
        self.root.bind_all("<Control-Alt-i>", self._toggle_visibility_event)

        # API key
        key = get_api_key()
        if not key:
            key = self._prompt_api_key()
        self.client = GrokAPIClient(key)

        # Apply capture exclusion once realized
        self.root.after(600, self._finish_init)

        # Close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        logger.info("GUI ready.")

    # ---- helpers ----
    def _append(self, prefix: str, text: str) -> None:
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{prefix}{text}\n")
        self.chat_display.see(tk.END)
        self.chat_display.configure(state=tk.DISABLED)

    def _append_user(self, t: str) -> None:
        self._append("You: ", t)

    def _append_bot(self, t: str) -> None:
        self._append("ChatGPT: ", t)

    def _append_sys(self, t: str) -> None:
        self._append("[System] ", t)

    def _prompt_api_key(self) -> str:
        while True:
            key = simpledialog.askstring(APP_TITLE, "Enter your OpenAI API Key:", show="*")
            if key and key.strip():
                try:
                    save_api_key(key.strip())
                    return key.strip()
                except Exception as exc:
                    messagebox.showerror(APP_TITLE, f"Failed to save API key: {exc}")
                    logger.error("API key save failed: %s", exc, exc_info=True)
            else:
                if messagebox.askyesno(APP_TITLE, "API key is required. Exit the app?"):
                    self.root.destroy()
                    raise SystemExit

    def _finish_init(self) -> None:
        try:
            hwnd = self.root.winfo_id()
            self.root.update_idletasks()

            label = set_window_excluded_from_capture(hwnd)
            self.status_var.set(f"Capture: {label}")
            logger.info("Exclusion status: %s", label)

            # Force repaint (nudged geometry)
            w, h = self.root.winfo_width(), self.root.winfo_height()
            self.root.geometry(f"{w+1}x{h+1}")
            self.root.update_idletasks()
            self.root.geometry(f"{w}x{h}")
            self.root.update_idletasks()
        except Exception as exc:
            logger.error("finish_init failed: %s", exc, exc_info=True)
            self._append_sys("Warning: Capture exclusion failed (see app.log).")

        self.input_entry.focus_set()

    # ---- events ----
    def _toggle_visibility_event(self, event=None):
        self.toggle_visibility()

    def toggle_visibility(self):
        try:
            if not self._hidden:
                self.root.withdraw()
                self._hidden = True
                logger.info("Window hidden.")
            else:
                self.root.deiconify()
                self.root.lift()
                self.root.attributes("-topmost", True)
                self._hidden = False
                self.input_entry.focus_set()
                logger.info("Window shown.")
        except Exception as exc:
            logger.error("Toggle failed: %s", exc, exc_info=True)
            self._append_sys("Warning: Could not toggle visibility (see app.log).")

    def _on_return(self, event):
        self.handle_send()

    def handle_send(self) -> None:
        query = self.input_var.get().strip()
        if not query:
            return

        self._append_user(query)
        self.input_var.set("")
        logger.info("Send -> len=%d", len(query))

        def ok(text: str):
            self.root.after(0, lambda: self._append_bot(text))

        def err(exc: Exception):
            logger.error("Query failed: %s", exc, exc_info=True)
            self.root.after(0, lambda: self._append_sys(f"Error: {exc}"))

        self.runner.run_coro(self.client.send_query(query), callback=ok, errback=err)

    def _on_close(self) -> None:
        logger.info("Closing.")
        try:
            self.runner.stop()
        finally:
            self.root.destroy()
