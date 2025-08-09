#!/usr/bin/env python3
"""
fix_spanish_ocr.py

Clean common OCR errors in the Spanish column (.col1) of dual-column HTML files.
- Only modifies text under div.row > div.col1 > p
- Leaves the English column (.col2) untouched
- Now ignores whitespace-only changes

Dependencies:
  pip install beautifulsoup4 lxml

Usage:
  python3 fix_spanish_ocr.py /path/to/folder
  python3 fix_spanish_ocr.py /path/to/folder --dry-run
"""

import re
import sys
import argparse
from pathlib import Path
from bs4 import BeautifulSoup

REPLACE_MAP = {
    "acomodadora": "acomodadora",
    "afios": "años",
    "ahf": "ahí",
    "algtin": "algún",
    "alñil": "albañil",
    "arañia": "araña",
    "asin": "así",
    "atin": "al fin",
    "bofetén": "bofetón",
    "casí": "casi",
    "conocñamos": "conociéramos",
    "corrñan": "corrían",
    "crei": "creí",
    "Cémo": "Cómo",
    "debfa": "debía",
    "debfan": "debían",
    "debia": "debía",
    "decidid": "decidió",
    "decidted": "decidió",
    "duefio": "dueño",
    "emulsién": "emulsión",
    "enderezd": "enderezó",
    "encontrdndote": "encontrándote",
    "est4s": "estás",
    "fbamos": "íbamos",
    "gird": "giró",
    "habfa": "había",
    "habia": "había",
    "habja": "había",
    "habrña": "habría",
    "incréible": "increíble",
    "inmévil": "inmóvil",
    "instantdneéo": "instantáneo",
    "Lan": "Lang",
    "lfvidas": "lívidas",
    "manña": "manía",
    "mas,": "más,",
    "mas.": "más.",
    "mfnimo": "mínimo",
    "mird": "mirá",
    "miré ": "miró ",
    "mismás": "mismas",
    "paulal": "paulatino",
    "pdjaro": "pájaro",
    "parecia": "parecía",
    "parecid": "pareció",
    "pensd": "pensó",
    "perñeccién": "perfección",
    "petulante y20": "petulante y",
    "podña": "podía",
    "prohibñan": "prohibían",
    "quiz4 ": "quizás",
    "querña": "quería",
    "reaparecfa": "reaparecía",
    "repetid": "repitió",
    "retrocedié": "retrocedió",
    "salidé": "salió",
    "sefior": "señor",
    "sefiar": "señar",
    "sefiore": "señore",
    "sefiora": "señora",
    "seflora": "señora",
    "senor": "señor",
    "senora": "señora",
    "subj": "subí",
    "sueñio": "sueño",
    "tambien": "también",
    "tenña": "tenía",
    "ufias": "uñas"
}

WORD_REGEX_FIXES = [
    # collapse "paulatino fino fino fino ..." → "paulatino"
    (re.compile(r'\bpaulatino(?:\s+fino)+\b', re.IGNORECASE), 'paulatino'),
    # collapse any immediate word repetition: "fino fino" → "fino", "muy muy muy" → "muy"
    (re.compile(r'\b(\w+)(?:\s+\1\b)+', re.IGNORECASE), r'\1'),
    # fix "Langgggg..." → "Lang" (handles trailing punctuation)
    (re.compile(r'\bLangg+(?=\b|\W)', re.IGNORECASE), 'Lang'),

    # --- keep your existing ones below ---
    (re.compile(r'([A-Za-z])f([oaie])'), r'\1ñ\2'),
    (re.compile(r'\bhabia\b', re.IGNORECASE), 'había'),
    (re.compile(r'\bdebia\b', re.IGNORECASE), 'debía'),
    (re.compile(r'\bparecia\b', re.IGNORECASE), 'parecía'),
    (re.compile(r'\bestas\b', re.IGNORECASE), 'estás'),
    (re.compile(r'\bestaba\b', re.IGNORECASE), 'estaba'),
    (re.compile(r'\bse[f|r]ior(a|as|es)?\b', re.IGNORECASE), 'señor\\1' if '\\1' else 'señor'),
]

EMBEDDED_DIGIT_MAP = {
    '4': 'a',
    '0': 'o',
    '6': 'ó',
    '1': 'l',
}

EMBEDDED_DIGIT_RE = re.compile(r'(?<=\w)[4016](?=\w)', re.UNICODE)
STANDALONE_NUM_RE = re.compile(r'\b\d{1,3}(?:,\d+)?\b')
MULTISPACE_RE = re.compile(r'[ \t]{2,}')
SPACE_BEFORE_PUNCT_RE = re.compile(r'\s+([,.;:!?])')
PUNCT_SPACING_REPAIRS = [
    (SPACE_BEFORE_PUNCT_RE, r'\1'),
    (MULTISPACE_RE, ' '),
]

def fix_embedded_digits(token: str) -> str:
    def repl(m):
        d = m.group(0)
        return EMBEDDED_DIGIT_MAP.get(d, d)
    return EMBEDDED_DIGIT_RE.sub(repl, token)

def clean_spanish_text(s: str) -> str:
    if not s:
        return s
        
    original = s
    
    for bad, good in REPLACE_MAP.items():
        s = s.replace(bad, good)
    for pat, repl in WORD_REGEX_FIXES:
        s = pat.sub(repl, s)
    
    if s == original:
        return s
        
    s = re.sub(r' +', ' ', s)
    s = re.sub(r' \)', ')', s)
    s = re.sub(r'\( ', '(', s)
    return s.strip()

def _is_safe_to_drop_number(text: str, start: int, end: int) -> bool:
    token = text[start:end]
    try:
        val = int(token.replace(',', ''))
    except ValueError:
        return False
    if val >= 1000:
        return False
    left = text[max(0, start - 1):start]
    right = text[end:end + 1]
    return (left == '' or not left.isalpha()) and (right == '' or not right.isalpha())

def process_file(path: Path, dry_run: bool = False) -> int:
    html = path.read_text(encoding='utf-8', errors='replace')
    soup = BeautifulSoup(html, 'lxml')
    changed = 0
    for row in soup.select('div.row'):
        col1 = row.select_one('div.col1')
        if not col1:
            continue
        ps = col1.find_all('p')
        for p in ps:
            before = p.get_text()
            after = clean_spanish_text(before)
            if after != before and after.strip() != before.strip():
                # === ADDED: print each change ===
                print(f"  • {path.name} | {before!r}  ->  {after!r}")
                # =================================
                changed += 1
                if not dry_run:
                    p.string = after
    if changed and not dry_run:
        path.write_text(str(soup), encoding='utf-8')
    return changed

def check_loops():
    bad_to_good = REPLACE_MAP
    loops = []
    for bad, good in bad_to_good.items():
        if good in bad_to_good and bad_to_good[good] != good:
            loops.append((bad, good))
    if loops:
        print("⚠️ Potential loops detected:")
        for b, g in loops:
            print(f"  {b} -> {g} and {g} -> {REPLACE_MAP[g]}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', type=str, help='Folder containing .html files')
    ap.add_argument('--dry-run', action='store_true', help='Analyze only, no write')
    args = ap.parse_args()
    check_loops()
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