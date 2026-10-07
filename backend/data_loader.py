from pathlib import Path
import json


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

UNIFIED_FILE = (
    DATA_DIR
    / "processed"
    / "unified"
    / "rag_documents.json"
)

SCHEMES_FILE = (
    DATA_DIR
    / "metadata"
    / "central_schemes.json"
)

SOURCES_FILE = (
    DATA_DIR
    / "metadata"
    / "central_sources.json"
)

RULES_FILE = (
    DATA_DIR
    / "metadata"
    / "central_eligibility_rules.json"
)


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_rag_documents():
    return load_json(UNIFIED_FILE)


def load_schemes():
    data = load_json(SCHEMES_FILE)

    if isinstance(data, dict):
        return data.get("schemes", [])

    return data


def load_sources():
    data = load_json(SOURCES_FILE)

    if isinstance(data, dict):
        return data.get("sources", [])

    return data


def load_rules():
    data = load_json(RULES_FILE)

    if isinstance(data, dict):
        return data.get("schemes", [])

    return data


def build_scheme_index():

    schemes = load_schemes()
    sources = load_sources()
    rules = load_rules()

    source_index = {
        item.get("scheme_id"): item
        for item in sources
        if item.get("scheme_id")
    }

    rule_index = {
        item.get("scheme_id"): item
        for item in rules
        if item.get("scheme_id")
    }

    index = {}

    for scheme in schemes:

        scheme_id = scheme.get("scheme_id")

        if not scheme_id:
            continue

        index[scheme_id] = {
            "scheme": scheme,
            "source": source_index.get(scheme_id, {}),
            "rules": rule_index.get(scheme_id, {}),
        }

    return index