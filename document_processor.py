from pathlib import Path
import pymupdf
import re

RAW_DIR = Path("data/raw/central")
OUTPUT_DIR = Path("data/processed/text")

MIN_TEXT_CHARS = 50

GARBAGE_CHARS = [
    "\x81",
    "\x8d",
    "\x8f",
    "\x90",
    "\x9d",
    "\xad",
    "‚",
    "ƒ",
    "„",
    "…",
    "†",
    "‡",
    "ˆ",
    "‰",
    "Š",
    "Ž",
]


def clean_text(text):
    text = text.replace("\r", "")
    text = text.replace("\x00", "")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def looks_garbled(text):
    if not text:
        return False

    garbage_count = sum(text.count(char) for char in GARBAGE_CHARS)

    # Detect obvious font-encoding corruption
    if garbage_count >= 3:
        return True

    # Detect excessive replacement/control characters
    control_chars = sum(
        1 for char in text
        if ord(char) < 32 and char not in "\n\t"
    )

    if control_chars >= 3:
        return True

    return False


def process_pdf(pdf_path):
    print(f"\nProcessing: {pdf_path.name}")

    doc = pymupdf.open(pdf_path)

    pages = []
    flagged_pages = []

    for page_number, page in enumerate(doc, start=1):

        text = page.get_text("text", sort=True)
        text = clean_text(text)

        if len(text) < MIN_TEXT_CHARS:
            flagged_pages.append(page_number)

            pages.append(
                f"--- PAGE {page_number} ---\n"
                "[OCR REQUIRED]"
            )

        elif looks_garbled(text):
            flagged_pages.append(page_number)

            pages.append(
                f"--- PAGE {page_number} ---\n"
                "[OCR REQUIRED]"
            )

        else:
            pages.append(
                f"--- PAGE {page_number} ---\n{text}"
            )

    doc.close()

    output_file = OUTPUT_DIR / f"{pdf_path.stem}.txt"

    encoded = "\n\n".join(pages).encode("utf-8")

    output_file.write_bytes(encoded)

    print(f"Pages: {len(pages)}")
    print(f"OCR required: {flagged_pages}")
    print(f"Saved: {output_file}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(RAW_DIR.glob("*.pdf"))

    print(f"Found {len(pdf_files)} PDF files.")

    for pdf in pdf_files:
        process_pdf(pdf)

    print("\nDocument processing completed.")


if __name__ == "__main__":
    main()