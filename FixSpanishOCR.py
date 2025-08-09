#!/usr/bin/env python3
"""
fix_spanish_ocr_simple.py

Radically simplified: ONLY do direct text replacements using the pairs in REPLACE_MAP.
- Processes HTML files in a folder
- Replaces text ONLY inside div.row > div.col1 > p
- Leaves the English column (.col2) untouched
- No regex, no logging, no extra logic
"""

import sys
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
    "ufias": "uñas",
    "inutiles": "inútiles",
    "atrds": "atrás",
    "parecña": "parecía",
    "mds": "más",
    "conseguña": "conseguía",
    "19a0": "1940",
    "perñección": "perfección",
    "bamos": "íbamos"
}

def clean_text_simple(s: str) -> str:
    for bad, good in REPLACE_MAP.items():
        s = s.replace(bad, good)
    return s

def process_file(path: Path) -> None:
    html = path.read_text(encoding='utf-8', errors='replace')
    soup = BeautifulSoup(html, 'lxml')
    modified = False

    for row in soup.select('div.row'):
        col1 = row.select_one('div.col1')
        if not col1:
            continue
        for p in col1.find_all('p'):
            before = p.get_text()
            after = clean_text_simple(before)
            if after != before:
                p.string = after
                modified = True

    if modified:
        path.write_text(str(soup), encoding='utf-8')

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 fix_spanish_ocr_simple.py /path/to/folder")
        sys.exit(2)

    folder = Path(sys.argv[1]).expanduser().resolve()
    if not folder.is_dir():
        print(f"❌ Not a directory: {folder}")
        sys.exit(2)

    for f in sorted(folder.glob('*.html')):
        process_file(f)

if __name__ == '__main__':
    main()