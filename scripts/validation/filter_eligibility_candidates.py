from pathlib import Path
import json
import re

INPUT_FILE = Path("data/metadata/central_eligibility_candidates.json")
OUTPUT_FILE = Path("data/metadata/central_eligibility_relevant.json")

STRONG_PATTERNS = [
    r"\beligibility criteria\b",
    r"\beligibility\b",
    r"\bwho can\b",
    r"\bwho is eligible\b",
    r"\beligible beneficiaries\b",
    r"\beligible beneficiary\b",
    r"\bbeneficiary\b",
    r"\bbeneficiaries\b",
    r"\bselection criteria\b",
    r"\bexclusion\b",
    r"\bnot eligible\b",
    r"\bineligible\b",
    r"\bconditions for\b",
    r"\bconditions of eligibility\b",
    r"\bminimum age\b",
    r"\bmaximum age\b",
    r"\bage limit\b",
    r"\bincome limit\b",
    r"\bincome ceiling\b",
    r"\brequired documents\b",
    r"\bdocuments required\b"
]


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def is_relevant(text):
    text = normalize(text)

    matches = []

    for pattern in STRONG_PATTERNS:
        if re.search(pattern, text):
            matches.append(pattern)

    return matches


def main():
    data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    results = []

    for item in data:
        text = item.get("text", "")
        matches = is_relevant(text)

        if not matches:
            continue

        results.append({
            "scheme_name": item["scheme_name"],
            "chunk_id": item["chunk_id"],
            "page_number": item["page_number"],
            "matched_patterns": matches,
            "text": text
        })

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            results,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("Filtering completed.")
    print(f"Relevant chunks: {len(results)}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()