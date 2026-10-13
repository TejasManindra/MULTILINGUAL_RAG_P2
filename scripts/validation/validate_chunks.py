from pathlib import Path
import json
import re


CHUNK_DIR = Path("data/processed/chunks")

MIN_CHUNK_LENGTH = 80


def validate_file(file_path):
    """Validate one chunk JSON file."""

    problems = []

    try:
        data = json.loads(
            file_path.read_text(
                encoding="utf-8"
            )
        )
    except Exception as e:
        return {
            "file": file_path.name,
            "chunks": 0,
            "problems": [f"Invalid JSON: {e}"]
        }

    if not isinstance(data, list):
        return {
            "file": file_path.name,
            "chunks": 0,
            "problems": ["JSON root is not a list"]
        }

    chunk_ids = set()

    for index, chunk in enumerate(data, start=1):

        required_fields = [
            "chunk_id",
            "scheme_name",
            "government_level",
            "source_file",
            "page_number",
            "chunk_number",
            "text"
        ]

        # Required field check
        for field in required_fields:

            if field not in chunk:
                problems.append(
                    f"Chunk {index}: missing '{field}'"
                )

        # Skip remaining checks if fields are missing
        if not all(
            field in chunk
            for field in required_fields
        ):
            continue

        chunk_id = chunk["chunk_id"]
        text = chunk["text"]

        # Duplicate ID
        if chunk_id in chunk_ids:
            problems.append(
                f"Chunk {index}: duplicate chunk_id "
                f"'{chunk_id}'"
            )

        chunk_ids.add(chunk_id)

        # Empty text
        if not isinstance(text, str) or not text.strip():
            problems.append(
                f"Chunk {index}: empty text"
            )
            continue

        # Suspiciously short chunk
        if len(text.strip()) < MIN_CHUNK_LENGTH:
            problems.append(
                f"Chunk {index}: very short "
                f"({len(text.strip())} chars)"
            )

        # Blank-page contamination
        if "[BLANK PAGE]" in text:
            problems.append(
                f"Chunk {index}: contains [BLANK PAGE]"
            )

        # OCR marker contamination
        if "[OCR REQUIRED]" in text:
            problems.append(
                f"Chunk {index}: contains [OCR REQUIRED]"
            )

        if "[OCR FAILED]" in text:
            problems.append(
                f"Chunk {index}: contains [OCR FAILED]"
            )

        # Common mojibake indicators
        mojibake_patterns = [
            "Ã¢",
            "Ãƒ",
            "â€™",
            "â€œ",
            "Â ",
            "Ã",
            "â€¦",
        ]

        for pattern in mojibake_patterns:

            if pattern in text:
                problems.append(
                    f"Chunk {index}: possible "
                    f"encoding issue '{pattern}'"
                )
                break

        # Page number validation
        if not isinstance(
            chunk["page_number"],
            int
        ):
            problems.append(
                f"Chunk {index}: invalid page number"
            )

        # Scheme name validation
        if not str(
            chunk["scheme_name"]
        ).strip():
            problems.append(
                f"Chunk {index}: missing scheme name"
            )

    return {
        "file": file_path.name,
        "chunks": len(data),
        "problems": problems
    }


def main():

    files = sorted(
        CHUNK_DIR.glob("*.json")
    )

    if not files:
        print("No chunk files found.")
        return

    print("=" * 70)
    print("RAG CHUNK QUALITY VALIDATION")
    print("=" * 70)

    total_chunks = 0
    total_problems = 0

    for file_path in files:

        result = validate_file(file_path)

        total_chunks += result["chunks"]
        total_problems += len(
            result["problems"]
        )

        print(
            f"\n{result['file']}"
        )

        print(
            f"Chunks: {result['chunks']}"
        )

        if result["problems"]:

            print(
                f"Problems: "
                f"{len(result['problems'])}"
            )

            # Show maximum 10 problems per file
            for problem in result["problems"][:10]:
                print(
                    f"  - {problem}"
                )

            if len(result["problems"]) > 10:
                print(
                    f"  ... and "
                    f"{len(result['problems']) - 10} more"
                )

        else:
            print("Status: PASS")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        f"Documents checked : {len(files)}"
    )

    print(
        f"Total chunks      : {total_chunks}"
    )

    print(
        f"Total problems    : {total_problems}"
    )

    if total_problems == 0:
        print("\nRESULT: PASS")
        print(
            "Corpus is ready for metadata extraction."
        )
    else:
        print("\nRESULT: REVIEW REQUIRED")
        print(
            "Fix the reported problems before "
            "continuing."
        )


if __name__ == "__main__":
    main()