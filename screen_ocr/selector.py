"""Click-and-drag screen region selector. Requires a real display."""

from __future__ import annotations

import tkinter as tk
from typing import Dict, Optional


def select_region() -> Optional[Dict[str, int]]:
    """Show a fullscreen dimmed overlay; user drags a rectangle.

    Returns {"left","top","width","height"} or None if cancelled (Esc).
    """
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.35)
    root.configure(bg="black", cursor="crosshair")
    root.attributes("-topmost", True)

    canvas = tk.Canvas(root, highlightthickness=0, bg="black")
    canvas.pack(fill="both", expand=True)

    start = {}
    rect_id = None
    result: Dict[str, int] = {}

    def on_press(event):
        nonlocal rect_id
        start["x"], start["y"] = event.x, event.y
        if rect_id:
            canvas.delete(rect_id)
        rect_id = canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="red", width=2
        )

    def on_drag(event):
        canvas.coords(rect_id, start["x"], start["y"], event.x, event.y)

    def on_release(event):
        x0, y0 = start["x"], start["y"]
        x1, y1 = event.x, event.y
        result.update(
            {
                "left": min(x0, x1),
                "top": min(y0, y1),
                "width": abs(x1 - x0),
                "height": abs(y1 - y0),
            }
        )
        root.destroy()

    def on_cancel(_event=None):
        result.clear()
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", on_cancel)

    label = tk.Label(
        root,
        text="Drag to select a region  •  Esc to cancel",
        fg="white",
        bg="black",
        font=("TkDefaultFont", 14),
    )
    label.place(relx=0.5, rely=0.05, anchor="center")

    root.mainloop()
    if result.get("width", 0) < 5 or result.get("height", 0) < 5:
        return None
    return result
