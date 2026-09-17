"""Transparent, always-on-top floating overlay showing live OCR results.

Requires a real display. All Tk calls happen on the main thread; worker
threads push updates through `update_text()` which is thread-safe.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional


class LiveOverlay:
    def __init__(
        self,
        on_refresh: Callable[[], None],
        interval_ms: int = 2000,
        title: str = "Screen OCR — live",
    ):
        self.on_refresh = on_refresh
        self.interval_ms = interval_ms
        self._paused = False
        self._after_id: Optional[str] = None

        self.root = tk.Tk()
        self.root.title(title)
        self.root.overrideredirect(True)          # borderless
        self.root.attributes("-topmost", True)   # always on top
        self.root.attributes("-alpha", 0.92)     # slight transparency
        self.root.configure(bg="#1e1e1e")

        header = tk.Frame(self.root, bg="#1e1e1e")
        header.pack(fill="x", padx=8, pady=(6, 0))
        tk.Label(header, text="🔍 " + title, fg="#7dd3fc", bg="#1e1e1e",
                 font=("TkDefaultFont", 11, "bold")).pack(side="left")
        self.status = tk.Label(header, text="● live", fg="#4ade80", bg="#1e1e1e",
                               font=("TkDefaultFont", 10))
        self.status.pack(side="right")

        self.text = tk.Text(
            self.root, width=52, height=14, wrap="word",
            bg="#1e1e1e", fg="#e5e5e5", relief="flat",
            font=("TkDefaultFont", 11),
        )
        self.text.pack(fill="both", expand=True, padx=8, pady=6)
        self.text.insert("1.0", "Waiting for first capture…")
        self.text.configure(state="disabled")

        bar = tk.Frame(self.root, bg="#1e1e1e")
        bar.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(bar, text="⟳ Refresh", command=self.refresh_now,
                  bg="#333", fg="white", relief="flat").pack(side="left", padx=2)
        self.pause_btn = tk.Button(bar, text="⏸ Pause", command=self.toggle_pause,
                                   bg="#333", fg="white", relief="flat")
        self.pause_btn.pack(side="left", padx=2)
        tk.Button(bar, text="✕ Close", command=self.close,
                  bg="#7f1d1d", fg="white", relief="flat").pack(side="right", padx=2)

        # Drag the borderless window by its header.
        header.bind("<ButtonPress-1>", self._drag_start)
        header.bind("<B1-Motion>", self._drag_move)
        self._drag = {}

        # Start near the top-right of the primary screen.
        self.root.update_idletasks()
        x = self.root.winfo_screenwidth() - 460
        self.root.geometry(f"440x360+{max(x, 0)}+60")

    # -- window dragging -------------------------------------------------
    def _drag_start(self, event):
        self._drag = {"x": event.x, "y": event.y}

    def _drag_move(self, event):
        dx = event.x - self._drag["x"]
        dy = event.y - self._drag["y"]
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    # -- public API ------------------------------------------------------
    def update_text(self, body: str, status_note: str = "● live"):
        """Thread-safe: call from any thread."""
        def _apply():
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            self.text.insert("1.0", body)
            self.text.configure(state="disabled")
            self.status.configure(text=status_note)
        self.root.after(0, _apply)

    def refresh_now(self):
        self.on_refresh()

    def toggle_pause(self):
        self._paused = not self._paused
        self.pause_btn.configure(text="▶ Resume" if self._paused else "⏸ Pause")
        if self._paused:
            if self._after_id:
                self.root.after_cancel(self._after_id)
                self._after_id = None
            self.status.configure(text="⏸ paused", fg="#fbbf24")
        else:
            self.status.configure(text="● live", fg="#4ade80")
            self.on_refresh()
            self._schedule()

    def _schedule(self):
        if not self._paused:
            self._after_id = self.root.after(self.interval_ms, self._tick)

    def _tick(self):
        if not self._paused:
            self.on_refresh()
        self._schedule()

    def run(self):
        self._schedule()
        self.root.mainloop()

    def close(self):
        if self._after_id:
            self.root.after_cancel(self._after_id)
        self.root.destroy()
