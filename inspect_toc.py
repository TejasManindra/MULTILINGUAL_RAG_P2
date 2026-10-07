from pathlib import Path
import json
import re

INPUT_DIR = Path("data/processed/chunks")

TOC_TERMS = [
    "eligibility",
    "eligible",
    "beneficiary",
    "beneficiaries",
    "target group",
    "target beneficiary",
    "exclusion",
    "selection criteria",
    "coverage",
    "criteria",
    "conditions",
    "documents",
    "application"
]


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def main():
    for file_path in sorted(INPUT_DIR.glob("*.json")):
        chunks = json.loads(
            file_path.read_text(encoding="utf-8")
        )

        print("\n" + "=" * 90)
        print(file_path.stem)
        print("=" * 90)

        found = 0

        for chunk in chunks:
            text = chunk.get("text", "")
            normalized = normalize(text)

            # TOC is normally near the beginning of a document
            if chunk.get("page_number", 999) > 15:
                continue

            matches = [
                term for term in TOC_TERMS
                if term in normalized
            ]

            if matches:
                print(
                    f"\nPage {chunk.get('page_number')} | "
                    f"{chunk.get('chunk_id')}"
                )
                print(text[:1200])
                found += 1

        print(f"\nTOC candidates: {found}")


if __name__ == "__main__":
    main()