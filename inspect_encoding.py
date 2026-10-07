import json
from pathlib import Path

files = [
    "Kisan Credit Card (KCC).json",
    "National Social Assistance Programme.json",
    "Pradhan Mantri Fasal Bima Yojana (PMFBY)_english_.json",
]

for filename in files:
    path = Path("data/processed/chunks") / filename
    chunks = json.loads(path.read_text(encoding="utf-8"))

    for i, chunk in enumerate(chunks, start=1):
        text = chunk["text"]

        if "Ã" in text:
            print(f"\n{filename}")
            print(f"Chunk: {i}")
            print(repr(text[:500]))