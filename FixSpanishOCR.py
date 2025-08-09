#!/usr/bin/env python3
"""
fix_spanish_ocr.py

Clean common OCR errors in the Spanish column (.col1) of dual-column HTML files.
- Only modifies text under div.row > div.col1 > p
- Leaves the English column (.col2) untouched
- Makes a .bak backup next to the original file

Dependencies:
  pip install beautifulsoup4 lxml

Usage:
  python3 fix_spanish_ocr.py /path/to/folder
  python3 fix_spanish_ocr.py /path/to/folder --dry-run
"""

import re
import sys
import shutil
import argparse
from pathlib import Path
from bs4 import BeautifulSoup

# --- Config --------------------------------------------------------------

# Simple replace map: exact tokens or small substrings frequently seen in OCR
REPLACE_MAP = {
    # common OCR swaps for ñ/í/á/é/ó/ú and friends
    "sefior": "señor",
    "sefiar": "señar",          # rare, keep for safety (you can delete if noisy)
    "seflora": "señora",
    "seflora": "señora",
    "sefiora": "señora",
    "sefiore": "señore",
    "senor": "señor",
    "senora": "señora",

    "habfa": "había",
    "habia": "había",
    "debfa": "debía",
    "debfan": "debían",
    "debia": "debía",
    "parecia": "parecía",
    "parecid": "pareció",  # may overhit; review
    "estaba": "estaba",    # placeholder (example of legit word so no change)

    "duefio": "dueño",
    "afios": "años",
    "mfnimo": "mínimo",
    "mismo": "mismo",      # guard no-op

    # common random casing/accents from sample
    "Trépat": "Trépat",    # keep as-is (proper name)
    "Alix": "Alix",        # keep as-is
    "Rose": "Rose",

    # obvious garbles from sample
    "est4s": "estás",
    "quiz4 ": "quizás", 
    "gird": "giró",
    "salidé": "salió",
    "miré ": "miró ",  # beware: crude; adjust if it misfires
    "pensd": "pensó",
    "enderezd": "enderezó",
    "decidid": "decidió",
    "decidted": "decidió",
    "reaparecfa": "reaparecía",
    "acomodadora": "acomodadora",  # no-op, example guard

    # common accent recoveries where OCR drops accents
    "tambien": "también",
    "subj": "subí",
    "estaba": "estaba",
    "mas ": "más ",
    "mas,": "más,",
    "mas.": "más.",
    "solo ": "sólo ",   # stylistic—consider disabling if you prefer RAE 2010
    "sólo ": "sólo ",
    "asi": "así",
    "aun ": "aún ",
    "aun,": "aún,",
    "aun.": "aún.",
}

# Word-level regex corrections (patterns applied on word boundaries)
WORD_REGEX_FIXES = [
    # ñ via 'n' + tilde-like OCR: fi → ñ (very common in older OCR)
    (re.compile(r'([A-Za-z])f([oaie])'), r'\1ñ\2'),  # crude; review results
    # common verbs missing accent (only when exact tokens)
    (re.compile(r'\bhabia\b', re.IGNORECASE), 'había'),
    (re.compile(r'\bdebia\b', re.IGNORECASE), 'debía'),
    (re.compile(r'\bparecia\b', re.IGNORECASE), 'parecía'),
    (re.compile(r'\bestas\b', re.IGNORECASE), 'estás'),
    (re.compile(r'\bestaba\b', re.IGNORECASE), 'estaba'),
    # sefior/serior variants → señor
    (re.compile(r'\bse[f|r]ior(a|as|es)?\b', re.IGNORECASE), 'señor\\1' if '\\1' else 'señor'),
]

# Leetspeak-like corrections only when a digit is embedded in letters
EMBEDDED_DIGIT_MAP = {
    '4': 'a',
    '0': 'o',
    '6': 'ó',  # risky; you may prefer 'o'
    '1': 'l',  # risky; often "l" vs "1"
}

EMBEDDED_DIGIT_RE = re.compile(r'(?<=\w)[4016](?=\w)', re.UNICODE)

# Standalone-number tokens to drop (likely page/artifact numbers)
STANDALONE_NUM_RE = re.compile(r'\b\d{1,3}(?:,\d+)?\b')

# Artifacts like “, . . .” or repeated punctuation/extra spaces
MULTISPACE_RE = re.compile(r'[ \t]{2,}')
SPACE_BEFORE_PUNCT_RE = re.compile(r'\s+([,.;:!?])')
PUNCT_SPACING_REPAIRS = [
    (SPACE_BEFORE_PUNCT_RE, r'\1'),
    (MULTISPACE_RE, ' '),
]

# --- Core cleaning -------------------------------------------------------

def fix_embedded_digits(token: str) -> str:
    def repl(m):
        d = m.group(0)
        return EMBEDDED_DIGIT_MAP.get(d, d)
    return EMBEDDED_DIGIT_RE.sub(repl, token)

def clean_spanish_text(s: str) -> str:
    if not s:
        return s

    original = s

    # 1) simple substring replacements (case sensitive)
    for bad, good in REPLACE_MAP.items():
        s = s.replace(bad, good)

    # 2) word-level regex fixes
    def word_fix(match):
        return match.expand(r'\1ñ\2')  # placeholder not used here

    for pat, repl in WORD_REGEX_FIXES:
        s = pat.sub(repl, s)

    # 3) embedded digit fixes inside words (e.g., est4s → estás)
    def embedded_word_fix(m):
        token = m.group(0)
        return fix_embedded_digits(token)

    s = re.sub(r'\w+', embedded_word_fix, s, flags=re.UNICODE)

    # 4) drop isolated small numbers that look like OCR crumbs
    #    (be cautious; remove only if surrounded by spaces or punctuation)
    s = STANDALONE_NUM_RE.sub(lambda m: '' if _is_safe_to_drop_number(s, m.start(), m.end()) else m.group(0), s)

    # 5) spacing & punctuation cleanup
    for pat, repl in PUNCT_SPACING_REPAIRS:
        s = pat.sub(repl, s)

    # final trim of leftover double spaces
    s = re.sub(r' +', ' ', s)
    s = re.sub(r' \)', ')', s)
    s = re.sub(r'\( ', '(', s)
    return s.strip()

def _is_safe_to_drop_number(text: str, start: int, end: int) -> bool:
    """
    Heuristic: drop small numbers when not adjacent to letters or currency,
    and not obviously a year (>= 1000). Keeps years & big numbers.
    """
    token = text[start:end]
    try:
        val = int(token.replace(',', ''))
    except ValueError:
        return False

    if val >= 1000:
        return False  # likely a year or meaningful number

    left = text[max(0, start - 1):start]
    right = text[end:end + 1]
    # drop if surrounded by space/punct (i.e., not glued to letters)
    return (left == '' or not left.isalpha()) and (right == '' or not right.isalpha())

# --- HTML processing -----------------------------------------------------

def process_file(path: Path, dry_run: bool = False) -> int:
    html = path.read_text(encoding='utf-8', errors='replace')
    soup = BeautifulSoup(html, 'lxml')  # fall back to 'html.parser' if needed

    changed = 0
    for row in soup.select('div.row'):
        col1 = row.select_one('div.col1')
        if not col1:
            continue
        # Process all <p> under col1
        ps = col1.find_all('p')
        for p in ps:
            before = p.get_text()
            after = clean_spanish_text(before)
            if after != before:
                changed += 1
                p.string = after  # replace text content only

    if changed and not dry_run:
        # backup
        backup = path.with_suffix(path.suffix + '.bak')
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(str(soup), encoding='utf-8')

    return changed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', type=str, help='Folder containing .html files')
    ap.add_argument('--dry-run', action='store_true', help='Analyze only, no write')
    args = ap.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"❌ Not a directory: {folder}")
        sys.exit(2)

    total_files = 0
    total_changes = 0
    for f in sorted(folder.glob('*.html')):
        total_files += 1
        changes = process_file(f, dry_run=args.dry_run)
        if changes:
            print(f"✅ {f.name}: {changes} paragraphs updated")
        else:
            print(f"— {f.name}: no changes")
        total_changes += changes

    print(f"\nDone. Files scanned: {total_files} | Paragraphs updated: {total_changes} | dry_run={args.dry_run}")

if __name__ == '__main__':
    main()