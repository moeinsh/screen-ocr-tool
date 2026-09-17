"""OCR engine: pure functions over PIL images.

Headless-safe — no display, no windows, no screen access. Everything here is
unit-testable with synthetic images.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from typing import List, Optional

from PIL import Image, ImageOps

try:
    import pytesseract
    from pytesseract import TesseractNotFoundError
except ImportError:  # pragma: no cover - handled at call time
    pytesseract = None
    TesseractNotFoundError = RuntimeError

# Matches integers, decimals, thousands-separated values, phone-ish groups,
# signed amounts. Applied per line so multi-line noise stays separated.
NUMBER_RE = re.compile(
    r"""
    [+-]?              # optional sign
    (?:
        \d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?   # 1,234 / 1 234 / 1,234.56
      | \d+\.\d+                            # 12.50
      | \(\d+\)                             # (415) style groups
      | \d[\d.\-]*\d                        # 555-0132, 4155550132
      | \d                                  # lone digit
    )
    """,
    re.VERBOSE,
)


@dataclass
class OcrLine:
    text: str
    confidence: float  # 0-100, -1 when the engine gives none


@dataclass
class OcrResult:
    text: str
    lines: List[OcrLine] = field(default_factory=list)
    numbers: List[str] = field(default_factory=list)
    mean_confidence: float = -1.0


def tesseract_available() -> bool:
    """True when the `tesseract` binary is on PATH."""
    return shutil.which("tesseract") is not None


def preprocess(image: Image.Image, scale: int = 2) -> Image.Image:
    """Normalize a capture for OCR: grayscale, upscale, autocontrast.

    Tesseract is happiest with tall, high-contrast glyphs; a 2x upscale is a
    cheap, big win for small on-screen text.
    """
    gray = ImageOps.grayscale(image)
    w, h = gray.size
    upscaled = gray.resize((w * scale, h * scale), Image.LANCZOS)
    return ImageOps.autocontrast(upscaled, cutoff=1)


def _check_engine() -> None:
    if pytesseract is None:
        raise RuntimeError(
            "pytesseract is not installed. Run: pip install -r requirements.txt"
        )
    if not tesseract_available():
        raise RuntimeError(
            "The Tesseract OCR engine binary was not found.\n"
            "Install it for your OS, e.g.:\n"
            "  Ubuntu/Debian:  sudo apt install tesseract-ocr\n"
            "  macOS:          brew install tesseract\n"
            "  Windows:        choco install tesseract  (or the UB Mannheim installer)"
        )


def extract_text(
    image: Image.Image,
    lang: str = "eng",
    psm: int = 6,
    do_preprocess: bool = True,
    min_confidence: float = 0.0,
) -> OcrResult:
    """Run OCR over a PIL image and return structured text + numbers.

    Args:
        image: any PIL image (screenshot region).
        lang: Tesseract language code(s), e.g. "eng" or "eng+deu".
        psm: page segmentation mode (6 = uniform block of text, good default).
        do_preprocess: apply grayscale/upscale/autocontrast first.
        min_confidence: drop lines below this word-level confidence (0-100).
    """
    _check_engine()
    work = preprocess(image) if do_preprocess else image
    config = f"--psm {psm}"

    data = pytesseract.image_to_data(
        work, lang=lang, config=config, output_type=pytesseract.Output.DICT
    )
    lines: List[OcrLine] = []
    confs: List[float] = []
    # Group words by (block, paragraph, line) to rebuild text lines.
    buckets: dict = {}
    n = len(data["text"])
    for i in range(n):
        word = (data["text"][i] or "").strip()
        if not word:
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1.0
        if conf >= 0 and conf < min_confidence:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        buckets.setdefault(key, []).append((word, conf))

    for key in sorted(buckets):
        words = buckets[key]
        line_text = " ".join(w for w, _ in words)
        word_confs = [c for _, c in words if c >= 0]
        line_conf = sum(word_confs) / len(word_confs) if word_confs else -1.0
        lines.append(OcrLine(text=line_text, confidence=line_conf))
        if line_conf >= 0:
            confs.append(line_conf)

    full_text = "\n".join(line.text for line in lines)
    result = OcrResult(
        text=full_text,
        lines=lines,
        mean_confidence=(sum(confs) / len(confs)) if confs else -1.0,
    )
    result.numbers = extract_numbers(full_text)
    return result


def extract_numbers(text: str) -> List[str]:
    """Pull number-like tokens (amounts, phones, quantities) out of OCR text."""
    found: List[str] = []
    for line in text.splitlines():
        for m in NUMBER_RE.finditer(line):
            token = m.group(0).strip(".,")
            if token.startswith("(") and token.endswith(")") and len(token) > 2:
                token = token[1:-1]
            if token and token not in found:
                found.append(token)
    return found
