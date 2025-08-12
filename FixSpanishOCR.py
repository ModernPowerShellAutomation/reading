#!/usr/bin/env python3
"""
FixSpanishOCR.py
- Rasterizes PDF pages (Poppler), OCRs with Tesseract (Spanish by default),
- Drops likely footnotes/page numbers,
- Cleans hyphenation/whitespace,
- Writes a single UTF-8 .txt.

Usage:
  python3 FixSpanishOCR.py input.pdf output.txt
"""

import os, re, sys, shutil, tempfile
from pathlib import Path
from statistics import median

# --- Config knobs (adjust if needed) ---
DPI = 350                        # 300–400 good balance
LANGS = "spa"                    # e.g., "spa+eng" for mixed content
BOTTOM_FOOTNOTE_RATIO = 0.22     # bottom X% considered footnote zone
SMALL_TEXT_FACTOR = 0.70         # line height < 70% of median => suspect
REMOVE_INLINE_MARKERS = True     # strip [12], (12), 12) when safe
DEHYPHENATE = True               # join hyphenated line breaks
# --------------------------------------

# Heuristics regexes
FOOTNOTE_LINE_RE = re.compile(r"^\s*\d{1,3}[\.\)]\s+")    # "2. ..." or "2) ..."
INLINE_MARKER_RE = re.compile(r"(?<!\w)(\[\d{1,3}\]|\(\d{1,3}\)|\d{1,3}\))")
PAGE_NUM_RE = re.compile(r"^\s*\d{1,4}\s*$")

# --- Imports that may not exist until env is ready ---
try:
    from pdf2image import convert_from_path
except Exception as e:
    print("❌ Missing pdf2image or Poppler. Install with:\n"
          "   brew install poppler && pip install pdf2image\n", file=sys.stderr)
    raise
try:
    import pytesseract
    from pytesseract import Output
except Exception as e:
    print("❌ Missing pytesseract / tesseract. Install with:\n"
          "   brew install tesseract tesseract-lang && pip install pytesseract\n", file=sys.stderr)
    raise
try:
    import pandas as pd
except Exception as e:
    print("❌ Missing pandas. Install with: pip install pandas", file=sys.stderr)
    raise


def find_poppler_path() -> str | None:
    """On macOS/Homebrew, Poppler lives in /opt/homebrew/opt/poppler/bin (arm64)
    or /usr/local/opt/poppler/bin (Intel). Return bin path if present."""
    candidates = [
        "/opt/homebrew/opt/poppler/bin",
        "/usr/local/opt/poppler/bin",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def ocr_page(image, psm=3):
    cfg = f"--oem 1 --psm {psm}"
    # Return DataFrame with TSV fields
    return pytesseract.image_to_data(image, lang=LANGS, config=cfg, output_type=Output.DATAFRAME)


def blocks_by_line(df):
    """Robustly reconstruct lines from Tesseract TSV DataFrame."""
    if df is None or getattr(df, "empty", True):
        return []

    # Keep only confident tokens
    sub = df[df.get("conf", -1) != -1].copy()

    # Coerce text to string safely (prevents .str errors)
    if "text" not in sub.columns:
        sub["text"] = ""
    sub["text"] = sub["text"].fillna("").astype(str)

    # Drop rows that become empty after strip
    sub = sub[sub["text"].str.strip() != ""]
    if sub.empty:
        return []

    # Group into lines
    lines = []
    for (blk, par, ln), g in sub.groupby(["block_num", "par_num", "line_num"], dropna=False):
        txt = " ".join(g["text"].tolist())
        x = int(g["left"].min())
        y = int(g["top"].min())
        w = int(g["width"].max())
        h = int(g["height"].max())
        lines.append({"text": txt, "x": x, "y": y, "w": w, "h": h})
    return lines


def clean_text_lines(lines, page_h):
    """Remove footnotes/page numbers based on position + size + numbering."""
    if not lines:
        return []

    med_h = median([ln["h"] for ln in lines]) if lines else 0
    cutoff_y = page_h * (1.0 - BOTTOM_FOOTNOTE_RATIO)

    kept = []
    for ln in lines:
        t, y, h = ln["text"], ln["y"], ln["h"]
        if not t.strip():
            continue
        # page number lines
        if PAGE_NUM_RE.match(t.strip()):
            continue

        is_bottom = y >= cutoff_y
        looks_like_fn = bool(FOOTNOTE_LINE_RE.match(t)) or (med_h and h < med_h * SMALL_TEXT_FACTOR)

        # Drop if bottom and looks like footnote (numbered or notably small)
        if is_bottom and looks_like_fn:
            continue

        kept.append(t)
    return kept


def normalize_text(pages_text: list[str]) -> str:
    txt = "\n".join(pages_text)

    if REMOVE_INLINE_MARKERS:
        # Avoid nuking 4-digit years by limiting to 1–3 digit patterns
        txt = INLINE_MARKER_RE.sub("", txt)

    if DEHYPHENATE:
        # Join hyphenated breaks: "civi-\n lización" -> "civilización"
        txt = re.sub(r"(\w)-\n(\w)", r"\1\2", txt)

    # Trim trailing spaces on lines, compress excessive blank lines
    txt = re.sub(r"[ \t]+\n", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)

    # Join lines within paragraphs (heuristic: if no terminal punctuation before single newline)
    txt = re.sub(r"(?<![.!?…:;])\n(?!\n)", " ", txt)

    # Normalize whitespace
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    return txt.strip()


def pdf_to_clean_txt(pdf_path: str, out_txt: str):
    poppler_path = find_poppler_path()
    kwargs = {}
    if poppler_path:
        kwargs["poppler_path"] = poppler_path

    # Convert pages to images
    images = convert_from_path(pdf_path, dpi=DPI, fmt="png", **kwargs)

    pages_text = []
    for i, img in enumerate(images, 1):
        df = ocr_page(img)
        lines = blocks_by_line(df)
        page_h = img.size[1]
        kept = clean_text_lines(lines, page_h)
        pages_text.append("\n".join(kept))

    txt = normalize_text(pages_text)
    Path(out_txt).write_text(txt, encoding="utf-8")
    print(f"✅ Wrote: {out_txt}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 FixSpanishOCR.py input.pdf output.txt")
        sys.exit(1)
    inp, outp = sys.argv[1], sys.argv[2]
    if not Path(inp).exists():
        print(f"❌ Input not found: {inp}")
        sys.exit(1)
    pdf_to_clean_txt(inp, outp)