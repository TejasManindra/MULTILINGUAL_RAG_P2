from pathlib import Path
import pymupdf
import pytesseract
from PIL import Image


RAW_DIR = Path("data/raw/central")
TEXT_DIR = Path("data/processed/text")

TESSERACT_PATH = r"C:\Users\T10000\AppData\Local\Tesseract-OCR\tesseract.exe"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def ocr_page(page):
    """Convert a PDF page to a high-resolution image and run Tesseract."""

    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(3, 3),
        alpha=False
    )

    image = Image.frombytes(
        "RGB",
        [pix.width, pix.height],
        pix.samples
    )

    text = pytesseract.image_to_string(
        image,
        lang="eng",
        config="--psm 6"
    ).strip()

    return text


def process_pdf(pdf_path):

    output_file = TEXT_DIR / f"{pdf_path.stem}.txt"

    if not output_file.exists():
        print(f"Text file not found: {output_file}")
        return

    doc = pymupdf.open(pdf_path)

    text = output_file.read_text(
        encoding="utf-8"
    )

    updated_text = text

    for page_number, page in enumerate(doc, start=1):

        failed_marker = (
            f"--- PAGE {page_number} ---\n"
            f"[OCR FAILED]"
        )

        required_marker = (
            f"--- PAGE {page_number} ---\n"
            f"[OCR REQUIRED]"
        )

        if failed_marker in updated_text:
            marker = failed_marker

        elif required_marker in updated_text:
            marker = required_marker

        else:
            continue

        print(
            f"OCR retry: {pdf_path.name} | "
            f"Page {page_number}"
        )

        try:
            ocr_text = ocr_page(page)

            if not ocr_text:
                ocr_text = "[OCR FAILED]"

        except Exception as e:
            print(f"Error: {e}")
            ocr_text = "[OCR FAILED]"

        replacement = (
            f"--- PAGE {page_number} ---\n"
            f"{ocr_text}"
        )

        updated_text = updated_text.replace(
            marker,
            replacement,
            1
        )

    output_file.write_text(
        updated_text,
        encoding="utf-8"
    )

    doc.close()


def main():

    TEXT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Only collect each PDF once.
    pdf_files = sorted(
        set(RAW_DIR.glob("*.pdf"))
    )

    print(f"Found {len(pdf_files)} PDF files.")

    for pdf in pdf_files:
        process_pdf(pdf)

    print("\nOCR retry completed.")


if __name__ == "__main__":
    main()