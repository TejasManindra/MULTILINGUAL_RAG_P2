from pathlib import Path

text_dir = Path("data/processed/text")

for path in sorted(text_dir.glob("*.txt")):
    text = path.read_text(encoding="utf-8")

    if "[OCR FAILED]" in text:
        pages = text.split("--- PAGE ")

        print(f"\n{path.name}")

        for page in pages:
            if "[OCR FAILED]" in page:
                page_number = page.split("---", 1)[0].strip()
                print(f"  OCR FAILED: page {page_number}")