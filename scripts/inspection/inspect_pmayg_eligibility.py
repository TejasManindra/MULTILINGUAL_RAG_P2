import json

FILE = "data/processed/chunks/PMAY-G for Rural Housing.json"

with open(FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

keywords = [
    "eligible",
    "eligibility",
    "selection of beneficiaries",
    "beneficiary selection",
    "permanent wait list",
    "SECC",
    "deprived",
    "household",
    "kutcha",
    "houseless",
    "housing deprivation"
]

for chunk in chunks:
    text = chunk["text"]
    lower = text.lower()

    if any(keyword.lower() in lower for keyword in keywords):
        print()
        print("=" * 90)
        print("PAGE:", chunk["page_number"])
        print("CHUNK:", chunk["chunk_id"])
        print("=" * 90)
        print(text)