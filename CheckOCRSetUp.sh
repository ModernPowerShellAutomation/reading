#!/usr/bin/env bash
set -e

echo "🔎 Checking Homebrew..."
if ! command -v brew >/dev/null 2>&1; then
  echo "❌ Homebrew not found. Install from https://brew.sh" && exit 1
fi
echo "✅ brew OK: $(brew --version | head -n1)"

echo "🔎 Checking Poppler (pdftoppm)..."
if ! command -v pdftoppm >/dev/null 2>&1; then
  echo "⚠️ Installing poppler..."
  brew install poppler
fi
echo "✅ poppler OK: $(pdftoppm -v 2>&1 | head -n1)"

echo "🔎 Checking Tesseract..."
if ! command -v tesseract >/dev/null 2>&1; then
  echo "⚠️ Installing tesseract..."
  brew install tesseract
fi
echo "✅ tesseract OK: $(tesseract --version | head -n1)"

echo "🔎 Checking Spanish language data for Tesseract..."
TESSDIR="$(tesseract --print-parameters | awk -F= '/tessdata-dir/ {print $2}' | tr -d ' ')"
if [[ -z "$TESSDIR" || ! -d "$TESSDIR" ]]; then
  # common default for brew
  TESSDIR="/opt/homebrew/share/tessdata"
fi
if [[ ! -f "$TESSDIR/spa.traineddata" ]]; then
  echo "⚠️ Spanish traineddata not found in $TESSDIR. Installing..."
  # brew formula usually includes langs; if missing:
  brew install tesseract-lang || true
  # re-check:
  if [[ ! -f "$TESSDIR/spa.traineddata" ]]; then
    echo "❌ Could not find spa.traineddata. You can manually place it in $TESSDIR"
    echo "   Download: https://github.com/tesseract-ocr/tessdata_fast or tessdata_best"
    exit 1
  fi
fi
echo "✅ Spanish data OK at: $TESSDIR"

echo "🔎 Checking Python..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ python3 not found. Install via brew: brew install python" && exit 1
fi
echo "✅ python3 OK: $(python3 --version)"

echo "🔎 Checking Python packages (pdf2image, pytesseract, pandas)..."
python3 - <<'PY'
import importlib, sys
missing=[]
for m in ("pdf2image","pytesseract","pandas"):
    try: importlib.import_module(m)
    except ImportError: missing.append(m)
if missing:
    print("⚠️ Installing:", " ".join(missing))
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
    print("✅ Installed:", " ".join(missing))
else:
    print("✅ All required packages present.")
PY

echo "🎉 All checks done."