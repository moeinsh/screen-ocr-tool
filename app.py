#!/usr/bin/env python3
"""Screen OCR — live region capture + OCR + floating overlay.

Usage:
    python app.py                      # drag-select a region, live overlay starts
    python app.py --once               # capture once, print text, exit
    python app.py --region 100,200,800,600 --interval 1.5
    python app.py --once --numbers-only

A display is required for --region selection and the overlay.
--once works headless only if --region is given (no selector popup).
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from datetime import datetime

from screen_ocr.ocr import OcrResult, extract_text


def parse_region(spec: str) -> dict:
    try:
        left, top, width, height = (int(v) for v in spec.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"bad --region {spec!r}; expected LEFT,TOP,WIDTH,HEIGHT"
        )
    return {"left": left, "top": top, "width": width, "height": height}


def format_result(result: OcrResult, numbers_only: bool = False) -> str:
    stamp = datetime.now().strftime("%H:%M:%S")
    out = [f"[{stamp}]"]
    if numbers_only:
        nums = result.numbers or ["(none found)"]
        out.append("Numbers: " + ", ".join(nums))
    else:
        out.append(result.text.strip() or "(no text detected)")
        if result.numbers:
            out.append("")
            out.append("Numbers: " + ", ".join(result.numbers))
    if result.mean_confidence >= 0:
        out.append(f"(avg confidence {result.mean_confidence:.0f}%)")
    return "\n".join(out)


def run_once(bbox: dict, lang: str, psm: int, numbers_only: bool) -> int:
    from screen_ocr.capture import grab_region

    image = grab_region(bbox)
    result = extract_text(image, lang=lang, psm=psm)
    print(format_result(result, numbers_only))
    return 0


def run_live(bbox: dict, lang: str, psm: int, interval: float, numbers_only: bool) -> int:
    from screen_ocr.capture import grab_region
    from screen_ocr.overlay import LiveOverlay

    latest = {"text": "Starting…"}
    lock = threading.Lock()

    def worker():
        while True:
            try:
                image = grab_region(bbox)
                result = extract_text(image, lang=lang, psm=psm)
                body = format_result(result, numbers_only)
            except Exception as exc:  # keep the overlay alive on errors
                body = f"(capture/OCR error: {exc})"
            with lock:
                latest["text"] = body
            overlay.update_text(body)
            time.sleep(interval)

    overlay = LiveOverlay(on_refresh=lambda: None, interval_ms=int(interval * 1000))
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    overlay.run()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Live screen-region OCR overlay.")
    parser.add_argument("--region", type=parse_region, default=None,
                        help="LEFT,TOP,WIDTH,HEIGHT (skips the selector)")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="seconds between re-captures (default 2.0)")
    parser.add_argument("--lang", default="eng", help="tesseract language(s), e.g. eng+deu")
    parser.add_argument("--psm", type=int, default=6, help="tesseract page seg mode")
    parser.add_argument("--once", action="store_true",
                        help="single capture printed to stdout, then exit")
    parser.add_argument("--numbers-only", action="store_true",
                        help="show only extracted numbers")
    args = parser.parse_args(argv)

    bbox = args.region
    if bbox is None:
        from screen_ocr.selector import select_region

        bbox = select_region()
        if bbox is None:
            print("Region selection cancelled.", file=sys.stderr)
            return 1

    if args.once:
        return run_once(bbox, args.lang, args.psm, args.numbers_only)
    return run_live(bbox, args.lang, args.psm, args.interval, args.numbers_only)


if __name__ == "__main__":
    sys.exit(main())
