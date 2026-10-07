import json
from pathlib import Path

files = Path("data/processed/chunks").glob("*.json")

for path in files:
    chunks = json.loads(path.read_text(encoding="utf-8"))

    short_chunks = [
        (i, chunk["text"])
        for i, chunk in enumerate(chunks, start=1)
        if len(chunk["text"]) < 80
    ]

    if short_chunks:
        print(f"\n{'=' * 70}")
        print(path.name)

        for i, text in short_chunks:
            print(f"\nChunk {i} ({len(text)} chars):")
            print(repr(text))