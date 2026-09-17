"""Headless OCR accuracy tests: synthetic PIL images -> full OCR pipeline.

Run:  python -m tests.test_ocr   (from the project root)
Exit code 0 = all cases pass, 1 = any failure.
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from screen_ocr.ocr import extract_numbers, extract_text, tesseract_available  # noqa: E402

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def make_image(lines, font_size=36, mono=False, width=900, bg="white", fg="black",
               pad=30, line_gap=14):
    font = ImageFont.truetype(FONT_MONO if mono else FONT_PATH, font_size)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    heights = [tmp.textbbox((0, 0), ln, font=font)[3] for ln in lines]
    height = pad * 2 + sum(heights) + line_gap * (len(lines) - 1)
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)
    y = pad
    for ln, lh in zip(lines, heights):
        draw.text((pad, y), ln, font=font, fill=fg)
        y += lh + line_gap
    return img


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def char_accuracy(expected: str, got: str) -> float:
    """Simple similarity: 1 - edit_distance / max_len (approx via difflib)."""
    import difflib

    a, b = normalize(expected), normalize(got)
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


CASES = [
    {
        "name": "invoice header (text + numbers)",
        "lines": ["INVOICE #INV-2041", "Date: 2026-09-17", "Total due: $1,234.56"],
        "font_size": 40,
    },
    {
        "name": "phone + amounts",
        "lines": ["Call +1 (415) 555-0132", "Balance 987.65 USD", "Qty 42"],
        "font_size": 40,
        "mono": True,
    },
    {
        "name": "paragraph block",
        "lines": [
            "The quick brown fox jumps over",
            "the lazy dog. Pack my box with",
            "five dozen liquor jugs!",
        ],
        "font_size": 34,
    },
    {
        "name": "small font",
        "lines": ["Order 77821 shipped", "Tracking 1Z 999 999 99"],
        "font_size": 22,
    },
    {
        "name": "dense numbers row",
        "lines": ["100 200 300 400 500", "1.5 2.75 3.125 0.99"],
        "font_size": 40,
        "mono": True,
    },
]

PASS_THRESHOLD = 0.90  # per-case character similarity to count as pass


def main() -> int:
    if not tesseract_available():
        print("SKIP: tesseract binary not found on PATH; install tesseract-ocr.")
        return 2

    failures = 0
    for case in CASES:
        img = make_image(
            case["lines"],
            font_size=case.get("font_size", 36),
            mono=case.get("mono", False),
        )
        result = extract_text(img)
        expected = "\n".join(case["lines"])
        acc = char_accuracy(expected, result.text)
        ok = acc >= PASS_THRESHOLD
        failures += 0 if ok else 1
        print(f"[{'PASS' if ok else 'FAIL'}] {case['name']}: "
              f"similarity={acc:.2%} (conf={result.mean_confidence:.0f}%)")
        if not ok:
            print(f"   expected: {expected!r}")
            print(f"   got:      {result.text!r}")

    # numbers-extraction unit check (no OCR involved)
    sample = "Total: $1,234.56\nCall (415) 555-0132\nQty 42"
    nums = extract_numbers(sample)
    nums_ok = all(tok in nums for tok in ["1,234.56", "415", "555-0132", "42"])
    print(f"[{'PASS' if nums_ok else 'FAIL'}] extract_numbers: {nums}")
    failures += 0 if nums_ok else 1

    print(f"\n{len(CASES) + 1 - failures}/{len(CASES) + 1} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
