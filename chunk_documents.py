from pathlib import Path
import re
import json


INPUT_DIR = Path("data/processed/text")
OUTPUT_DIR = Path("data/processed/chunks")

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def clean_text(text):
    text = text.replace("\r", "")
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_noise_paragraphs(text):
    """
    Remove repeated headers, footer text,
    page-number artifacts, and obvious PDF
    extraction garbage.
    """

    lines = text.splitlines()

    cleaned = []

    noise_patterns = [
        r"^Guidelines for Pradhan Mantri Kaushal Vikas Yojana 4\.0$",
        r"^Pradhan Mantri Awas Yojana \(Urban\) 2\.0\s*:\s*Scheme Guidelines$",
        r"^Ministry of Housing and Urban Affairs$",
        r"^Contents$",
    ]

    for line in lines:

        line = line.strip()

        if not line:
            cleaned.append("")
            continue

        # Remove repeated document headers
        if any(
            re.fullmatch(pattern, line)
            for pattern in noise_patterns
        ):
            continue

        # Remove obvious PDF extraction garbage.
        # Only remove it when the line is short,
        # contains very few alphabetic characters,
        # and contains suspicious font characters.
        letters = sum(
            char.isalpha()
            for char in line
        )

        suspicious_chars = any(
            char in line
            for char in [
                "«",
                "»",
                "ƒ",
                "‚",
                "„",
                "†",
            ]
        )

        if (
            len(line) < 40
            and letters < 10
            and suspicious_chars
        ):
            continue

        cleaned.append(line)

    return "\n".join(cleaned)


def split_into_pages(text):
    """Split processed document using page markers."""

    pattern = r"--- PAGE (\d+) ---\n"

    matches = list(
        re.finditer(pattern, text)
    )

    pages = []

    for i, match in enumerate(matches):

        page_number = int(
            match.group(1)
        )

        start = match.end()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        page_text = text[
            start:end
        ].strip()

        pages.append(
            {
                "page_number": page_number,
                "text": page_text,
            }
        )

    return pages


def split_text(text, chunk_size=1200):
    """Create coherent chunks from paragraphs."""

    paragraphs = [
        p.strip()
        for p in re.split(
            r"\n\s*\n",
            text
        )
        if p.strip()
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:

        # Ignore page-number-only fragments
        if re.fullmatch(
            r"\d+",
            paragraph
        ):
            continue

        candidate = (
            f"{current}\n\n{paragraph}"
            if current
            else paragraph
        )

        if len(candidate) <= chunk_size:

            current = candidate
            continue

        if current:
            chunks.append(
                current.strip()
            )

        # Handle very large paragraphs
        if len(paragraph) > chunk_size:

            sentences = re.split(
                r"(?<=[.!?])\s+",
                paragraph
            )

            current = ""

            for sentence in sentences:

                sentence = sentence.strip()

                if not sentence:
                    continue

                candidate = (
                    f"{current} {sentence}"
                    if current
                    else sentence
                )

                if len(candidate) <= chunk_size:

                    current = candidate

                else:

                    if current:
                        chunks.append(
                            current.strip()
                        )

                    current = sentence

        else:

            current = paragraph

    if current:
        chunks.append(
            current.strip()
        )

    # Merge very short fragments into
    # the previous chunk when possible.
    cleaned_chunks = []

    for chunk in chunks:

        chunk = chunk.strip()

        if not chunk:
            continue

        if len(chunk) < 80:

            if cleaned_chunks:

                cleaned_chunks[-1] += (
                    "\n\n" + chunk
                )

            else:

                cleaned_chunks.append(
                    chunk
                )

        else:

            cleaned_chunks.append(
                chunk
            )

    return cleaned_chunks


def process_document(file_path):

    print(
        f"\nProcessing: {file_path.name}"
    )

    text = file_path.read_text(
        encoding="utf-8"
    )

    pages = split_into_pages(text)

    chunks = []

    chunk_counter = 1

    scheme_name = file_path.stem

    for page in pages:

        page_number = page[
            "page_number"
        ]

        # Clean extracted text
        page_text = clean_text(
            page["text"]
        )

        # Remove headers and PDF artifacts
        page_text = remove_noise_paragraphs(
            page_text
        )

        if not page_text:
            continue

        # Ignore intentionally blank pages
        if page_text == "[BLANK PAGE]":
            continue

        # Safety check: don't allow OCR
        # markers into the RAG corpus.
        if (
            "[OCR FAILED]" in page_text
            or "[OCR REQUIRED]" in page_text
        ):
            print(
                f"WARNING: OCR marker found "
                f"in {file_path.name} "
                f"page {page_number}"
            )
            continue

        page_chunks = split_text(
            page_text,
            CHUNK_SIZE
        )

        for chunk in page_chunks:

            chunks.append(
                {
                    "chunk_id": (
                        f"{scheme_name}_"
                        f"p{page_number}_"
                        f"c{chunk_counter}"
                    ),
                    "scheme_name": scheme_name,
                    "government_level": "central",
                    "source_file": file_path.name,
                    "page_number": page_number,
                    "chunk_number": chunk_counter,
                    "text": chunk,
                }
            )

            chunk_counter += 1

    output_file = (
        OUTPUT_DIR
        / f"{file_path.stem}.json"
    )

    output_file.write_text(
        json.dumps(
            chunks,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Pages processed : {len(pages)}"
    )

    print(
        f"Chunks created  : {len(chunks)}"
    )

    print(
        f"Saved           : {output_file}"
    )


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    files = sorted(
        INPUT_DIR.glob("*.txt")
    )

    if not files:

        print(
            "No processed text files found."
        )

        return

    print(
        f"Found {len(files)} "
        f"processed documents."
    )

    for file_path in files:

        process_document(
            file_path
        )

    print(
        "\nChunking completed."
    )


if __name__ == "__main__":
    main()