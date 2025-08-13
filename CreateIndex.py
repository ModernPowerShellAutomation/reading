import os
import re
from bs4 import BeautifulSoup
from urllib.parse import quote

DOCS_DIR = "docs"
OUTPUT_FILE = os.path.join(DOCS_DIR, "index.html")

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Reading</title>
  <style>
    body {{
      font-family: sans-serif;
      max-width: 800px;
      margin: 2rem auto;
      line-height: 1.6;
      padding: 0 1rem;
    }}
    h1 {{ margin-bottom: 2rem; }}
    .folder {{
      margin-bottom: 1rem;
      cursor: pointer;
    }}
    .folder-title {{
      font-weight: bold;
      padding: 0.5rem 0;
      border-bottom: 1px solid #ddd;
    }}
    .folder-contents {{
      display: none;
      padding-left: 1rem;
    }}
    .folder-contents a {{
      display: block;
      padding: 0.25rem 0;
      color: #06c;
      text-decoration: none;
    }}
    .folder-contents a:hover {{
      text-decoration: underline;
    }}
  </style>
</head>
<body>
  <h1>Reading</h1>
  <div id="content">
    {content}
  </div>

<script>
  document.querySelectorAll('.folder-title').forEach(title => {{
    title.addEventListener('click', () => {{
      const contents = title.nextElementSibling;
      const current = window.getComputedStyle(contents).display;
      contents.style.display = current === 'none' ? 'block' : 'none';
    }});
  }});
</script>
</body>
</html>
"""

def extract_number(title):
    match = re.search(r'Part (\d+)', title)
    return int(match.group(1)) if match else float('inf')

def extract_language_cefr(title):
    match = re.search(r'\((.+?)\s([A-C]\d(?:\.\d)?)\s*,', title)
    if match:
        language = match.group(1).strip()
        cefr = match.group(2).strip()
        return f"({language} {cefr})"
    return ""

def get_files_by_folder():
    entries = []
    for root, _, files in os.walk(DOCS_DIR):
        for file in files:
            if file.endswith(".html") and file != "index.html":
                rel_path = os.path.relpath(os.path.join(root, file), DOCS_DIR)
                filename = quote(rel_path.replace("\\", "/"))
                folder = os.path.dirname(rel_path)
                folder_name = folder if folder != "." else "Root"

                # Extract title from <title> tag if available
                with open(os.path.join(root, file), encoding="utf-8") as f:
                    soup = BeautifulSoup(f, "html.parser")
                    title_tag = soup.title
                    title = title_tag.string.strip() if title_tag and title_tag.string else file

                number = extract_number(title)

                # ✅ New conditional logic
                if number != float('inf'):
                    # If there's a "Part N" in the title, keep original style
                    link_title = f"{folder_name}: page {number}"
                else:
                    if folder_name == "Vulgate":
                        # For Vulgate folder, just show the filename without extension
                        base_name = os.path.splitext(file)[0]
                        link_title = base_name
                    else:
                        # Default fallback for other folders
                        link_title = f"{folder_name}: untitled"

                entries.append({
                    "filename": filename,
                    "folder": folder_name,
                    "title": title,
                    "number": number,
                    "link_title": link_title
                })
    return entries

def generate_index():
    entries = get_files_by_folder()
    grouped = {}
    for e in entries:
        grouped.setdefault(e["folder"], []).append(e)

    sections = []
    for folder, files in sorted(grouped.items()):
        sorted_files = sorted(files, key=lambda x: (x["number"], x["title"]))
        items = "\n".join(
            f'<a href="{e["filename"]}" target="_blank">{e["link_title"]}</a>'
            for e in sorted_files
        )
        sections.append(
            f'<div class="folder">'
            f'<div class="folder-title">{folder}</div>'
            f'<div class="folder-contents">{items}</div>'
            f'</div>'
        )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.format(content="\n".join(sections)))

    print(f"Index created here: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_index()