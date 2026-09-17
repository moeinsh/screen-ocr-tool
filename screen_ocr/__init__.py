"""screen_ocr — live screen-region capture + OCR + floating overlay.

Display-dependent modules (capture, selector, overlay) are imported lazily so
that `screen_ocr.ocr` stays importable and testable on headless machines.
"""

from .ocr import OcrLine, OcrResult, extract_numbers, extract_text, preprocess

__all__ = ["OcrLine", "OcrResult", "extract_numbers", "extract_text", "preprocess"]
