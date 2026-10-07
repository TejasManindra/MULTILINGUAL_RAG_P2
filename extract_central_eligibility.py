from pathlib import Path
import json
import re

INPUT_DIR = Path("data/processed/chunks")
OUTPUT_FILE = Path("data/metadata/central_eligibility_candidates.json")

KEYWORDS = [
    "eligibility",
    "eligible",
    "eligibility criteria",
    "beneficiary",
    "beneficiaries",
    "who can",
    "who is eligible",
    "criteria",
    "age limit",
    "income",
    "income limit",
    "occupation",
    "documents required",
    "required documents",
    "application",
    "benefit",
    "benefits",
    "exclusion",
    "not eligible",
    "ineligible",
    "selection criteria",
    "conditions",
]


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def keyword_matches(text):
    normalized = normalize(text)
    return [keyword for keyword in KEYWORDS if keyword in normalized]


def extract_candidates():
    results = []

    files = sorted(INPUT_DIR.glob("*.json"))

    for file_path in files:
        chunks = json.loads(file_path.read_text(encoding="utf-8"))

        scheme_name = file_path.stem

        for chunk in chunks:
            text = chunk.get("text", "")
            matches = keyword_matches(text)

            if not matches:
                continue

            results.append({
                "scheme_name": scheme_name,
                "chunk_id": chunk.get("chunk_id"),
                "page_number": chunk.get("page_number"),
                "matched_keywords": matches,
                "text": text
            })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("Extraction completed.")
    print(f"Candidate chunks: {len(results)}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    extract_candidates()