# Screen OCR — live region capture + OCR overlay

A small Python desktop tool: drag-select any screen region, and a transparent
always-on-top window shows the text (and numbers) inside it, updating live.

## What it does

- **Region select** — fullscreen picker, click-and-drag, Esc cancels
- **Capture** — fast region screenshots via `mss`
- **OCR** — Tesseract via `pytesseract`, with grayscale + 2x upscale preprocessing
- **Numbers** — amounts, phones, quantities pulled out into their own line
- **Live overlay** — borderless, semi-transparent, always-on-top window with
  Refresh / Pause / Close controls; re-captures on a timer (default 2 s)

## Install

```bash
pip install -r requirements.txt
```

You also need the Tesseract OCR **engine** (not a Python package):

| OS      | Command |
|---------|---------|
| Ubuntu/Debian | `sudo apt install tesseract-ocr` |
| macOS   | `brew install tesseract` |
| Windows | `choco install tesseract` (or the UB Mannheim installer) |

## Run

```bash
python app.py                                # select region, live overlay starts
python app.py --region 100,200,800,600       # skip the picker
python app.py --interval 1.5                 # re-capture every 1.5 s
python app.py --once --numbers-only          # single shot, numbers only, to stdout
python app.py --lang eng+deu                 # extra OCR languages
```

## Tests (headless-safe)

```bash
python -m tests.test_ocr
```

Generates synthetic text/number images with PIL, runs the full OCR pipeline,
and reports per-case similarity. No display needed.

## Project layout

```
app.py                 CLI / entry point
screen_ocr/
  ocr.py               OCR engine — pure PIL in/out, headless-safe
  capture.py           mss screen capture (needs a display)
  selector.py          drag-to-select region UI (needs a display)
  overlay.py           transparent always-on-top window (needs a display)
tests/
  test_ocr.py          synthetic-image accuracy tests
```

Display-dependent code lives in `capture.py`, `selector.py`, `overlay.py` and
is only imported when actually used, so `screen_ocr.ocr` imports and tests
cleanly on headless machines/CI.

## 30-second client demo script

1. `python app.py` → drag a box around any text on screen (a receipt, an
   invoice PDF, a chat window).
2. The floating overlay pops up showing the recognized text **and** a
   "Numbers:" line with every amount/phone/quantity found.
3. Change something inside the region (scroll, type a new number) → the
   overlay refreshes automatically within 2 seconds.
4. Hit **⏸ Pause** to freeze a result, **⟳ Refresh** for an instant re-read,
   drag the overlay anywhere by its header.

Talking points: *"Everything runs locally — no cloud, no API keys, your data
never leaves the machine. The same pipeline also works as a one-shot CLI for
batch jobs."*

---

**Author:** Moein Shahidi — [@moeinsh](https://github.com/moeinsh)

© 2026 Moein Shahidi. Released under the MIT License.
