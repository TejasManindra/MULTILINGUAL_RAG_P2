from pathlib import Path
import json


BASE_DIR = Path("data")
CHUNKS_DIR = BASE_DIR / "processed" / "chunks"
METADATA_DIR = BASE_DIR / "metadata"
OUTPUT_DIR = BASE_DIR / "processed" / "unified"

OUTPUT_FILE = OUTPUT_DIR / "rag_documents.json"


# Exact mapping between Central chunk filenames
# and the validated scheme IDs.
FILE_TO_SCHEME = {
    "Ayushman Bharat PM-JAY.json": "PM_JAY",
    "Central Sector Scholarship Scheme.json": "CSSS",
    "Guidelines of PMAY-U-2.json": "PMAY_U_2",
    "Kisan Credit Card (KCC).json": "KCC",
    "National Social Assistance Programme.json": "NSAP",
    "PM SVANidhi Scheme Guidelines.json": "PM_SVANIDHI",
    "PM Vishwakarma-Guidelines.json": "PM_VISHWAKARMA",
    "PM-KISAN(English).json": "PM_KISAN",
    "PMAY-G for Rural Housing.json": "PMAY_G",
    "PMKVY-Guidelines.json": "PMKVY",
    "Pradhan Mantri Fasal Bima Yojana (PMFBY)_english_.json": "PMFBY",
    "Pradhana Mantri MUDRA Yojana.json": "PM_MUDRA",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_items(data, key):
    if isinstance(data, dict):
        return data.get(key, [])
    return data


def build_lookup(items):
    return {
        item["scheme_id"]: item
        for item in items
        if item.get("scheme_id")
    }


def get_source_url(source):
    return (
        source.get("source_url")
        or source.get("official_url")
        or source.get("url")
        or ""
    )


def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load validated Central metadata
    schemes_data = load_json(
        METADATA_DIR / "central_schemes.json"
    )

    sources_data = load_json(
        METADATA_DIR / "central_sources.json"
    )

    rules_data = load_json(
        METADATA_DIR / "central_eligibility_rules.json"
    )

    schemes = get_items(schemes_data, "schemes")
    sources = get_items(sources_data, "sources")
    rules = get_items(rules_data, "schemes")

    scheme_lookup = build_lookup(schemes)
    source_lookup = build_lookup(sources)
    rule_lookup = build_lookup(rules)

    documents = []

    print("=" * 60)
    print("BUILDING CENTRAL RAG DATASET")
    print("=" * 60)

    print(f"Central schemes : {len(schemes)}")
    print(f"Central sources : {len(sources)}")
    print(f"Central rules   : {len(rules)}")

    missing_files = []
    unknown_scheme_ids = []

    for filename, scheme_id in FILE_TO_SCHEME.items():

        chunk_file = CHUNKS_DIR / filename

        if not chunk_file.exists():
            missing_files.append(filename)
            continue

        if scheme_id not in scheme_lookup:
            unknown_scheme_ids.append(scheme_id)
            continue

        chunks = load_json(chunk_file)

        scheme = scheme_lookup[scheme_id]
        source = source_lookup.get(scheme_id, {})
        rule = rule_lookup.get(scheme_id, {})

        for chunk in chunks:

            text = chunk.get("text", "").strip()

            if not text:
                continue

            document = {
                "chunk_id": chunk.get("chunk_id"),

                "scheme_id": scheme_id,

                "scheme_name": (
                    scheme.get("official_scheme_name")
                    or scheme.get("scheme_name")
                    or chunk.get("scheme_name")
                ),

                "government_level": "central",

                "state": scheme.get("state"),

                "ministry_department": scheme.get(
                    "ministry_department"
                ),

                "category": scheme.get("category"),

                "subcategory": scheme.get("subcategory"),

                "target_beneficiary": scheme.get(
                    "target_beneficiary"
                ),

                "scheme_status": scheme.get(
                    "scheme_status"
                ),

                "benefit_description": scheme.get(
                    "benefit_description"
                ),

                "eligibility_rules": rule.get(
                    "eligibility_rules", []
                ),

                "exclusion_rules": rule.get(
                    "exclusion_rules", []
                ),

                "verification_status": rule.get(
                    "verification_status"
                ),

                "source_url": get_source_url(source),

                "source_status": source.get("status"),

                "source_file": chunk.get(
                    "source_file"
                ),

                "document_title": source.get(
                    "document_title"
                ),

                "page_number": chunk.get(
                    "page_number"
                ),

                "chunk_number": chunk.get(
                    "chunk_number"
                ),

                "text": text,
            }

            documents.append(document)

        print(
            f"{scheme_id:20} "
            f"{len(chunks):4} chunks"
        )

    documents.sort(
        key=lambda x: (
            x["scheme_id"],
            x.get("page_number") or 0,
            x.get("chunk_number") or 0,
        )
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            documents,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("\n" + "=" * 60)
    print("CENTRAL RAG DATASET CREATED")
    print("=" * 60)

    print(f"Total chunks : {len(documents)}")

    unique_schemes = sorted(
        set(x["scheme_id"] for x in documents)
    )

    print(f"Unique schemes : {len(unique_schemes)}")

    print("\nSchemes included:")

    for scheme_id in unique_schemes:
        count = sum(
            1
            for x in documents
            if x["scheme_id"] == scheme_id
        )
        print(f"  {scheme_id:20} {count:4}")

    print("\nValidation:")

    missing_text = sum(
        not x.get("text")
        for x in documents
    )

    missing_scheme_id = sum(
        not x.get("scheme_id")
        for x in documents
    )

    missing_source_url = sum(
        not x.get("source_url")
        for x in documents
    )

    print(f"Missing text       : {missing_text}")
    print(f"Missing scheme_id  : {missing_scheme_id}")
    print(f"Missing source URL : {missing_source_url}")

    if missing_files:
        print("\nMissing chunk files:")
        for filename in missing_files:
            print(f"  {filename}")

    if unknown_scheme_ids:
        print("\nUnknown scheme IDs:")
        for scheme_id in unknown_scheme_ids:
            print(f"  {scheme_id}")

    print(f"\nOutput: {OUTPUT_FILE}")
    print("\nDone.")


if __name__ == "__main__":
    main()