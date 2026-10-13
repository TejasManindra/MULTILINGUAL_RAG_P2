import json

file_path = "data/processed/chunks/PMAY-G for Rural Housing.json"

with open(file_path, "r", encoding="utf-8") as f:
    chunks = json.load(f)

for chunk in chunks:
    if chunk["page_number"] in [7, 8, 9]:
        print()
        print("=" * 80)
        print("PAGE:", chunk["page_number"])
        print("CHUNK:", chunk["chunk_id"])
        print("=" * 80)
        print(chunk["text"])