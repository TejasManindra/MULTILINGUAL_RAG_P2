from pathlib import Path
import json
import re

INPUT_FILE = Path("data/metadata/central_eligibility_relevant.json")

HEADING_PATTERNS = [
    r"^eligibility.*$",
    r".*eligibility criteria.*",
    r".*eligible beneficiaries.*",
    r".*beneficiary.*",
    r".*beneficiaries.*",
    r".*who can.*",
    r".*criteria.*",
    r".*conditions.*",
    r".*exclusion.*",
    r".*not eligible.*",
    r".*ineligible.*",
    r".*selection.*criteria.*",
]


def looks_like_heading(text):
    text = text.strip()

    if len(text) > 180:
        return False

    lines = text.splitlines()

    if len(lines) > 8:
        return False

    for line in lines:
        line = line.strip()

        if not line:
            continue

        for pattern in HEADING_PATTERNS:
            if re.match(pattern, line, re.IGNORECASE):
                return True

    return False


def main():
    data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    seen = set()
    results = []

    for item in data:
        text = item.get("text", "").strip()

        if not looks_like_heading(text):
            continue

        key = (
            item["scheme_name"],
            item["page_number"],
            text
        )

        if key in seen:
            continue

        seen.add(key)

        results.append({
            "scheme_name": item["scheme_name"],
            "page_number": item["page_number"],
            "chunk_id": item["chunk_id"],
            "text": text
        })

    print(f"Possible eligibility sections: {len(results)}")
    print()

    current_scheme = None

    for item in results:
        if item["scheme_name"] != current_scheme:
            current_scheme = item["scheme_name"]
            print("\n" + "=" * 80)
            print(current_scheme)
            print("=" * 80)

        print(
            f"\nPage {item['page_number']} | "
            f"{item['chunk_id']}"
        )
        print(item["text"][:500])


if __name__ == "__main__":
    main()