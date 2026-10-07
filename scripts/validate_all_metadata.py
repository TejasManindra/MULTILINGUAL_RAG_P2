from pathlib import Path
import json

BASE = Path("data/metadata")

DATASETS = {
    "Central": {
        "schemes": "central_schemes.json",
        "sources": "central_sources.json",
        "rules": "central_eligibility_rules.json",
    },
    "Telangana": {
        "schemes": "telangana_schemes.json",
        "sources": "telangana_sources.json",
        "rules": "telangana_eligibility_rules.json",
    },
    "Andhra Pradesh": {
        "schemes": "andhra_pradesh_schemes.json",
        "sources": "andhra_pradesh_sources.json",
        "rules": "andhra_pradesh_eligibility_rules.json",
    },
}

VALID_STATUSES = {
    "CURRENT",
    "CURRENT_REFERENCE",
    "CURRENT_SOURCE_AVAILABLE",
    "CURRENT_SOURCE_NEEDS_VERIFICATION",
    "CURRENT_PROGRAM_ACTIVE",
    "CURRENT_PROGRAM_ACTIVE_RULES_NEED_CURRENT_NOTIFICATION",
    "CURRENT_PROGRAM_ACTIVE_RULES_NEED_CATEGORY_NORMALIZATION",
    "CURRENT_PROGRAM_RULES_NEED_CURRENT_BENEFIT_VERIFICATION",
    "CURRENT_PROGRAMS_NEED_COMPONENT_MAPPING",
    "CURRENT_PROGRAMS_NEED_COMPONENT_NORMALIZATION",
    "CURRENT_BENEFICIARY_DATA_AVAILABLE_BUT_RULES_NEED_VERIFICATION",
    "CURRENT_PORTAL_ACTIVE",
    "CURRENT_PORTAL_SOURCE_AVAILABLE",
    "WEB_VERIFIED_CURRENT",
    "HISTORICAL_REFERENCE",
    "HISTORICAL_RULES_RETAINED_CURRENT_STATUS_NEEDS_VERIFICATION",
    "DO_NOT_USE_AS_CURRENT_RULE_BLOCK",
    "CURRENT_REFERENCE",
}

errors = []
warnings = []


def load_json(filename):
    path = BASE / filename

    if not path.exists():
        errors.append(f"Missing file: {filename}")
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"Invalid JSON: {filename} -> {e}")
        return None


for dataset_name, files in DATASETS.items():

    print(f"\n{'=' * 60}")
    print(dataset_name)
    print(f"{'=' * 60}")

    schemes_data = load_json(files["schemes"])
    sources_data = load_json(files["sources"])
    rules_data = load_json(files["rules"])

    if not schemes_data or not sources_data or not rules_data:
        continue

    schemes = schemes_data.get("schemes", [])
    sources = sources_data.get("sources", [])
    rules = rules_data.get("schemes", [])

    scheme_ids = [x.get("scheme_id") for x in schemes]
    source_ids = [x.get("scheme_id") for x in sources]
    rule_ids = [x.get("scheme_id") for x in rules]

    print(f"Schemes : {len(scheme_ids)}")
    print(f"Sources : {len(source_ids)}")
    print(f"Rules   : {len(rule_ids)}")

    # Duplicate scheme IDs
    for name, ids in [
        ("scheme catalog", scheme_ids),
        ("source registry", source_ids),
        ("eligibility rules", rule_ids),
    ]:
        duplicates = sorted({x for x in ids if ids.count(x) > 1})

        if duplicates:
            errors.append(
                f"{dataset_name}: duplicate IDs in {name}: {duplicates}"
            )

    scheme_set = set(scheme_ids)
    source_set = set(source_ids)
    rule_set = set(rule_ids)

    missing_sources = sorted(scheme_set - source_set)
    missing_rules = sorted(scheme_set - rule_set)

    extra_sources = sorted(source_set - scheme_set)
    extra_rules = sorted(rule_set - scheme_set)

    if missing_sources:
        errors.append(
            f"{dataset_name}: schemes missing sources: {missing_sources}"
        )

    if missing_rules:
        errors.append(
            f"{dataset_name}: schemes missing rules: {missing_rules}"
        )

    if extra_sources:
        warnings.append(
            f"{dataset_name}: source entries without scheme: {extra_sources}"
        )

    if extra_rules:
        warnings.append(
            f"{dataset_name}: rule entries without scheme: {extra_rules}"
        )

    # Check source URLs
    for source in sources:
        scheme_id = source.get("scheme_id")
        url = source.get("url")

        if not url:
            errors.append(
                f"{dataset_name}: {scheme_id} has no source URL"
            )

        if url and not url.startswith("http"):
            errors.append(
                f"{dataset_name}: {scheme_id} has invalid URL: {url}"
            )

        status = source.get("status")

        if status and status not in VALID_STATUSES:
            warnings.append(
                f"{dataset_name}: {scheme_id} has unrecognized source status: {status}"
            )

    # Check eligibility rule structure
    for rule in rules:
        scheme_id = rule.get("scheme_id")

        if "eligibility_rules" not in rule:
            errors.append(
                f"{dataset_name}: {scheme_id} missing eligibility_rules"
            )

        if "exclusion_rules" not in rule:
            errors.append(
                f"{dataset_name}: {scheme_id} missing exclusion_rules"
            )

        if "verification_status" not in rule:
            warnings.append(
                f"{dataset_name}: {scheme_id} missing verification_status"
            )

    # Check master scheme names
    for scheme in schemes:
        if not scheme.get("scheme_id"):
            errors.append(
                f"{dataset_name}: scheme without scheme_id"
            )

        if not scheme.get("official_scheme_name"):
            errors.append(
                f"{dataset_name}: {scheme.get('scheme_id')} missing official_scheme_name"
            )

print("\n")
print("=" * 60)
print("FINAL VALIDATION")
print("=" * 60)

if errors:
    print("\nERRORS:")
    for error in errors:
        print("[ERROR]", error)
else:
    print("\nNo structural errors found.")

if warnings:
    print("\nWARNINGS:")
    for warning in warnings:
        print("[WARNING]", warning)
else:
    print("\nNo warnings.")

print("\n")

if errors:
    print("RESULT: FAILED")
    raise SystemExit(1)
else:
    print("RESULT: PASSED")