import os
from bs4 import BeautifulSoup

def remove_source_language_line(root_folder):
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            if filename.lower().endswith(".html"):
                file_path = os.path.join(dirpath, filename)

                # Read the HTML file
                with open(file_path, "r", encoding="utf-8") as f:
                    soup = BeautifulSoup(f, "html.parser")

                # Find all tags that contain the text "Source Language"
                for tag in soup.find_all(string=lambda text: text and "Source Language" in text):
                    # Remove the parent element (entire line/section)
                    if tag.parent:
                        tag.parent.decompose()

                # Save the modified HTML back
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(soup))

                print(f"✅ Cleaned: {file_path}")

# === Run it ===
if __name__ == "__main__":
    folder_path = "/Users/mikegallagher/repos/Archive/reading-1/docs"  # Change this!
    remove_source_language_line(folder_path)
    print("🎉 Done!")