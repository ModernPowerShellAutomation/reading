import os
from bs4 import BeautifulSoup

# ===== CONFIGURATION =====
INPUT_FOLDER = r"/Users/mikegallagher/repos/Archive/reading-1/docs/Guerre"
# ========================

def process_html_file(file_path):
    """Remove English columns (col2) and save with '_es' suffix in the same folder."""
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # Remove all English columns (div.col2)
    for col2 in soup.find_all('div', class_='col2'):
        col2.decompose()

    # Generate new filename (append '_es' before .html)
    base_name = os.path.basename(file_path)
    name, ext = os.path.splitext(base_name)
    new_name = f"{name}_es{ext}"
    output_path = os.path.join(os.path.dirname(file_path), new_name)

    # Save modified HTML
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    print(f"Processed: {base_name} → {new_name}")

def main():
    # Process all HTML files in INPUT_FOLDER
    for filename in os.listdir(INPUT_FOLDER):
        if filename.lower().endswith('.html'):
            file_path = os.path.join(INPUT_FOLDER, filename)
            process_html_file(file_path)

    print(f"\nDone! Spanish-only files saved in: {INPUT_FOLDER}")

if __name__ == "__main__":
    main()