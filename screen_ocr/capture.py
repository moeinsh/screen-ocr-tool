"""Screen capture. Requires a real display (fails headless — by design)."""

from __future__ import annotations

from typing import Dict, List

from PIL import Image

import mss


def grab_region(bbox: Dict[str, int]) -> Image.Image:
    """Capture a screen region and return it as a PIL image.

    bbox: {"left": int, "top": int, "width": int, "height": int}
    """
    with mss.mss() as sct:
        shot = sct.grab(
            {
                "left": int(bbox["left"]),
                "top": int(bbox["top"]),
                "width": int(bbox["width"]),
                "height": int(bbox["height"]),
            }
        )
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def list_monitors() -> List[Dict[str, int]]:
    """Return available monitors (index 0 = virtual full desktop)."""
    with mss.mss() as sct:
        return [
            {"left": m["left"], "top": m["top"], "width": m["width"], "height": m["height"]}
            for m in sct.monitors
        ]
