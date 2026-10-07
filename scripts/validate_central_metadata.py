from pathlib import Path
import json

BASE = Path("data/metadata")

FILES = [
    "central_schemes.json",
    "central_sources.json",
    "central_eligibility_rules.json",
]

for filename in FILES:
    path = BASE / filename

    if not path.exists():
        print(f"[ERROR] Missing: {path}")
        continue

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"[OK] {filename}")

        if filename == "central_schemes.json":
            print(f"     Schemes: {len(data['schemes'])}")

        elif filename == "central_eligibility_rules.json":
            print(f"     Schemes: {len(data['schemes'])}")
            print(f"     Version: {data.get('dataset', {}).get('version')}")

    except Exception as e:
        print(f"[ERROR] {filename}: {e}")

print("\nValidation completed.")