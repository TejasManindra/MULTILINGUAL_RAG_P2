from pathlib import Path
import json
import re

FILE = Path(
    "data/processed/chunks/Ayushman Bharat PM-JAY.json"
)

KEYWORDS = [
    "eligibility",
    "eligible",
    "beneficiary",
    "beneficiaries",
    "exclusion",
    "not eligible",
    "ineligible",
    "entitled",
    "coverage",
    "family",
    "household",
    "income",
    "deprivation",
    "SECC",
    "documents",
    "residence"
]


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


chunks = json.loads(FILE.read_text(encoding="utf-8"))

matches = []

for chunk in chunks:
    text = chunk.get("text", "")
    normalized = normalize(text)

    found = [
        keyword
        for keyword in KEYWORDS
        if keyword.lower() in normalized
    ]

    if found:
        matches.append({
            "page": chunk.get("page_number"),
            "chunk_id": chunk.get("chunk_id"),
            "keywords": found,
            "text": text
        })


for item in matches:
    print("\n" + "=" * 100)
    print("PAGE:", item["page"])
    print("CHUNK:", item["chunk_id"])
    print("KEYWORDS:", ", ".join(item["keywords"]))
    print("-" * 100)
    print(item["text"])