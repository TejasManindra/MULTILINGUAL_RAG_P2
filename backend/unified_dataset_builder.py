import json
import re
from pathlib import Path
from typing import Any


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = ROOT / "data" / "raw"
AP_DIR = RAW_DIR / "andhra_pradesh"
TG_DIR = RAW_DIR / "telangana"

UNIFIED_DIR = ROOT / "data" / "processed" / "unified"
UNIFIED_FILE = UNIFIED_DIR / "rag_documents.json"


# ============================================================
# CONFIG
# ============================================================

CHUNK_SIZE = 2200
CHUNK_OVERLAP = 300

EXPECTED_KEYS = [
    "chunk_id",
    "scheme_id",
    "scheme_name",
    "government_level",
    "state",
    "ministry_department",
    "category",
    "subcategory",
    "target_beneficiary",
    "scheme_status",
    "benefit_description",
    "eligibility_rules",
    "exclusion_rules",
    "verification_status",
    "source_url",
    "source_status",
    "source_file",
    "document_title",
    "page_number",
    "chunk_number",
    "text",
]


# ============================================================
# HELPERS
# ============================================================

def clean_text(text: str) -> str:
    """
    Normalize whitespace without destroying Markdown structure.
    """

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Normalize spaces/tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_filename_stem(file_path: Path) -> str:
    """
    Return a clean source filename without .md/.txt suffixes.

    Examples:

        Aadabidda Nidhi.md.txt
            -> Aadabidda Nidhi

        Scheme.md
            -> Scheme

        Scheme.txt
            -> Scheme
    """

    name = file_path.name

    lower_name = name.lower()

    if lower_name.endswith(".md.txt"):
        name = name[:-7]

    elif lower_name.endswith(".txt"):
        name = name[:-4]

    elif lower_name.endswith(".md"):
        name = name[:-3]

    return name.strip()


def normalize_scheme_id(value: str) -> str:
    """
    Create a stable normalized scheme ID.
    """

    value = value.strip().upper()

    value = re.sub(
        r"[^A-Z0-9]+",
        "_",
        value,
    )

    value = re.sub(
        r"_+",
        "_",
        value,
    )

    return value.strip("_")


def extract_field(
    text: str,
    field_name: str,
) -> str | None:
    """
    Extract a metadata field from Markdown/text.

    Supports:

        Field: value
        **Field:** value
        - Field: value
        * Field: value
        Field : value
        **Field** : value

    Matching is case-insensitive.
    """

    pattern = (
        rf"(?im)"
        rf"^\s*"
        rf"(?:[-*]\s*)?"
        rf"(?:\*\*)?"
        rf"{re.escape(field_name)}"
        rf"(?:\*\*)?"
        rf"\s*:\s*"
        rf"(.+?)"
        rf"\s*$"
    )

    match = re.search(
        pattern,
        text,
    )

    if match:

        value = clean_text(
            match.group(1)
        )

        value = value.strip(
            "*_ "
        )

        return value or None

    return None


def extract_url_from_text(
    text: str,
) -> str | None:
    """
    Extract the first HTTP/HTTPS URL from the source text.

    This is only used as a fallback when an explicit URL field
    was not found.
    """

    # Markdown URL:
    # [Official Website](https://example.com)
    markdown_match = re.search(
        r"\[[^\]]+\]\((https?://[^)\s]+)\)",
        text,
        flags=re.IGNORECASE,
    )

    if markdown_match:

        return markdown_match.group(1).strip()

    # Plain URL
    url_match = re.search(
        r"https?://[^\s<>\])}]+",
        text,
        flags=re.IGNORECASE,
    )

    if url_match:

        return url_match.group(0).rstrip(
            ".,;:)"
        )

    return None


def extract_section(
    text: str,
    start_heading: str,
    next_heading_pattern: str | None = None,
) -> str:
    """
    Extract a Markdown section.

    Supports:

        ## 4. Eligibility Criteria
        ## Eligibility Criteria
        ### Eligibility Criteria
        ## 4) Eligibility Criteria
        ## 4 - Eligibility Criteria

    The heading number is ignored.

    The next Markdown heading marks the end of the section.
    """

    heading_title = (
        start_heading
        .replace("#", "")
        .strip()
    )

    # Remove leading numbering.
    #
    # Examples:
    # 4. Eligibility Criteria
    # 4) Eligibility Criteria
    # 4 - Eligibility Criteria
    #
    heading_title = re.sub(
        r"^\s*\d+\s*[\.\)\-:]*\s*",
        "",
        heading_title,
    )

    escaped_title = re.escape(
        heading_title
    )

    pattern = (
        rf"(?ims)"
        rf"^\s*#+\s*"
        rf"(?:\d+\s*[\.\)\-:]*\s*)?"
        rf"{escaped_title}"
        rf"\s*$"
        rf"(.*?)"
        rf"(?=^\s*#+\s+|\Z)"
    )

    match = re.search(
        pattern,
        text,
    )

    if match:

        return clean_text(
            match.group(1)
        )

    return ""


def find_section_by_keywords(
    text: str,
    keywords: list[str],
) -> str:
    """
    Find a Markdown heading containing one of the supplied
    keywords and return its section content.

    Used as a fallback for source documents whose heading is
    not exactly 'Eligibility Criteria'.
    """

    pattern = (
        r"(?ims)"
        r"^\s*#+\s*"
        r"(?:\d+\s*[\.\)\-:]*\s*)?"
        r"([^\n]+?)"
        r"\s*$"
    )

    matches = list(
        re.finditer(
            pattern,
            text,
        )
    )

    for index, match in enumerate(matches):

        heading = clean_text(
            match.group(1)
        ).lower()

        heading = re.sub(
            r"^\s*\d+\s*[\.\)\-:]*\s*",
            "",
            heading,
        )

        if not any(
            keyword.lower() in heading
            for keyword in keywords
        ):
            continue

        section_start = match.end()

        if index + 1 < len(matches):

            section_end = matches[
                index + 1
            ].start()

        else:

            section_end = len(text)

        section = text[
            section_start:section_end
        ]

        section = clean_text(
            section
        )

        if section:

            return section

    return ""


def parse_money(
    value: str | None,
) -> Any:
    """
    Convert simple Indian currency values to numbers.
    """

    if not value:
        return None

    value = value.replace(
        ",",
        "",
    )

    value = value.replace(
        "₹",
        "",
    )

    value = value.replace(
        "Rs.",
        "",
    )

    value = value.replace(
        "Rs",
        "",
    )

    numbers = re.findall(
        r"\d+(?:\.\d+)?",
        value,
    )

    if not numbers:
        return None

    try:

        number = float(
            numbers[0]
        )

        if number.is_integer():

            return int(number)

        return number

    except ValueError:

        return None


# ============================================================
# SCHEME ID HELPERS
# ============================================================

def is_invalid_scheme_id(
    value: str | None,
) -> bool:
    """
    Detect placeholder values.
    """

    if value is None:
        return True

    normalized = clean_text(
        str(value)
    ).strip().lower()

    invalid_values = {
        "",
        "not specified",
        "not specified in the verified source",
        "not specified in verified source",
        "not available",
        "not provided",
        "not mentioned",
        "not mentioned in the verified source",
        "n/a",
        "na",
        "none",
        "null",
        "-",
        "--",
    }

    return normalized in invalid_values


def fallback_scheme_id(
    scheme_name: str | None,
    state: str | None,
    government_level: str,
    file_path: Path | None = None,
) -> str:
    """
    Generate a deterministic source-specific scheme ID.

    If the source does not provide a valid Scheme ID and the
    scheme name is also unavailable, the source filename is used.

    This prevents different documents from receiving the same ID.
    """

    level = (
        government_level or ""
    ).strip().lower()

    state_normalized = (
        state or ""
    ).strip().lower()

    # --------------------------------------------------------
    # Infer state from source directory
    # --------------------------------------------------------

    if file_path is not None:

        parent_name = (
            file_path.parent.name
            .strip()
            .lower()
        )

        if parent_name == "andhra_pradesh":

            state_normalized = (
                "andhra pradesh"
            )

        elif parent_name == "telangana":

            state_normalized = (
                "telangana"
            )

    # --------------------------------------------------------
    # Prefix
    # --------------------------------------------------------

    if level == "central":

        prefix = "CENTRAL"

    elif state_normalized == "andhra pradesh":

        prefix = "AP"

    elif state_normalized == "telangana":

        prefix = "TS"

    else:

        prefix = "STATE"

    # --------------------------------------------------------
    # Base identity
    # --------------------------------------------------------

    base_name = scheme_name

    if is_invalid_scheme_id(
        base_name
    ):

        if file_path is not None:

            base_name = clean_filename_stem(
                file_path
            )

        else:

            base_name = "UNKNOWN_SCHEME"

    normalized_name = normalize_scheme_id(
        str(base_name)
    )

    # --------------------------------------------------------
    # Final safety fallback
    # --------------------------------------------------------

    if (
        not normalized_name
        or normalized_name
        == "NOT_SPECIFIED_IN_THE_VERIFIED_SOURCE"
    ):

        if file_path is not None:

            normalized_name = normalize_scheme_id(
                clean_filename_stem(
                    file_path
                )
            )

        else:

            normalized_name = (
                "UNKNOWN_SCHEME"
            )

    if not normalized_name:

        normalized_name = (
            "UNKNOWN_SCHEME"
        )

    return (
        f"{prefix}_{normalized_name}"
    )


# ============================================================
# ELIGIBILITY EXTRACTION
# ============================================================

def build_eligibility_rules(
    text: str,
    source_file: str,
    chunk_id: str,
):
    """
    Extract explicitly documented eligibility information.

    No eligibility rule is inferred.

    If the source has a structured eligibility section but uses
    unfamiliar field labels, the section is preserved as
    eligibility_text.
    """

    # --------------------------------------------------------
    # Try common exact section names
    # --------------------------------------------------------

    section = ""

    possible_headings = [
        "Eligibility Criteria",
        "Eligibility",
        "Eligibility Requirements",
        "Eligibility Conditions",
        "Eligibility Rules",
        "Who is Eligible",
        "Eligible Beneficiaries",
        "Eligibility and Conditions",
        "Eligibility Requirements and Conditions",
    ]

    for heading in possible_headings:

        section = extract_section(
            text,
            heading,
        )

        if section:

            break

    # --------------------------------------------------------
    # Fallback: search heading keywords
    # --------------------------------------------------------

    if not section:

        section = find_section_by_keywords(
            text,
            [
                "eligibility",
                "eligible",
                "beneficiary criteria",
            ],
        )

    # --------------------------------------------------------
    # Search text
    # --------------------------------------------------------

    search_text = (
        section
        if section
        else text
    )

    rules = []

    # --------------------------------------------------------
    # Known explicit fields
    # --------------------------------------------------------

    field_mapping = {

        "Age Requirement":
            "age",

        "Age Criteria":
            "age",

        "Age":
            "age",

        "Gender Requirement":
            "gender",

        "Gender Criteria":
            "gender",

        "Gender":
            "gender",

        "Residence Requirement":
            "residence",

        "Residence Criteria":
            "residence",

        "Residence":
            "residence",

        "Residential Requirement":
            "residence",

        "Income Requirement":
            "family_income",

        "Income Criteria":
            "family_income",

        "Income Limit":
            "family_income",

        "Family Income":
            "family_income",

        "Annual Family Income":
            "family_income",

        "Occupation Requirement":
            "occupation",

        "Occupation Criteria":
            "occupation",

        "Occupation":
            "occupation",

        "Education Requirement":
            "education",

        "Education Criteria":
            "education",

        "Education":
            "education",

        "Land Requirement":
            "land",

        "Land Criteria":
            "land",

        "Land Holding":
            "land",

        "Land Requirement / Holding":
            "land",

        "Social Category Requirement":
            "social_category",

        "Social Category":
            "social_category",

        "Caste Requirement":
            "social_category",

        "Category Requirement":
            "social_category",

        "Community Requirement":
            "social_category",

        "Target Beneficiary":
            "beneficiary",

        "Target Beneficiaries":
            "beneficiary",

        "Beneficiary":
            "beneficiary",

        "Beneficiaries":
            "beneficiary",

        "Other Eligibility":
            "other",

        "Eligibility Conditions":
            "other",

    }

    found_fields = set()

    for label, field in field_mapping.items():

        value = extract_field(
            search_text,
            label,
        )

        if not value:

            continue

        if field in found_fields:

            continue

        found_fields.add(
            field
        )

        rules.append(
            {
                "field": field,
                "operator":
                    "documented_requirement",
                "value": value,
                "condition_group":
                    "eligibility",
                "source": {
                    "file": source_file,
                    "page": None,
                    "chunk_id": chunk_id,
                },
            }
        )

    # --------------------------------------------------------
    # Preserve structured eligibility text
    # --------------------------------------------------------

    if section and not rules:

        rules.append(
            {
                "field":
                    "eligibility_text",

                "operator":
                    "documented_requirement",

                "value":
                    section,

                "condition_group":
                    "eligibility",

                "source": {
                    "file": source_file,
                    "page": None,
                    "chunk_id": chunk_id,
                },
            }
        )

    return rules


# ============================================================
# EXCLUSION EXTRACTION
# ============================================================

def build_exclusion_rules(
    text: str,
    source_file: str,
    chunk_id: str,
):
    """
    Extract explicitly stated exclusions.
    """

    exclusion_section = ""

    possible_headings = [
        "Exclusions",
        "Exclusion Criteria",
        "Exclusion Rules",
        "Who is Not Eligible",
        "Not Eligible",
    ]

    for heading in possible_headings:

        exclusion_section = (
            extract_section(
                text,
                heading,
            )
        )

        if exclusion_section:

            break

    if not exclusion_section:

        exclusion_section = (
            find_section_by_keywords(
                text,
                [
                    "exclusion",
                    "not eligible",
                ],
            )
        )

    if not exclusion_section:

        return []

    return [
        {
            "field":
                "explicit_exclusion",

            "operator":
                "documented_exclusion",

            "value":
                exclusion_section,

            "condition_group":
                "exclusion",

            "source": {
                "file": source_file,
                "page": None,
                "chunk_id": chunk_id,
            },
        }
    ]


# ============================================================
# SOURCE METADATA
# ============================================================

def get_metadata(
    text: str,
    file_path: Path,
    government_level: str,
):

    # --------------------------------------------------------
    # Basic fields
    # --------------------------------------------------------

    scheme_name = extract_field(
        text,
        "Scheme Name",
    )

    official_name = extract_field(
        text,
        "Official Scheme Name",
    )

    scheme_id = extract_field(
        text,
        "Scheme ID",
    )

    state = extract_field(
        text,
        "State",
    )

    department = (
        extract_field(
            text,
            "Department",
        )
        or extract_field(
            text,
            "Ministry / Department",
        )
        or extract_field(
            text,
            "Ministry",
        )
    )

    category = extract_field(
        text,
        "Category",
    )

    subcategory = extract_field(
        text,
        "Subcategory",
    )

    status = (
        extract_field(
            text,
            "Scheme Status",
        )
        or extract_field(
            text,
            "Status",
        )
    )

    target = (
        extract_field(
            text,
            "Target Beneficiary",
        )
        or extract_field(
            text,
            "Target Beneficiaries",
        )
        or extract_field(
            text,
            "Beneficiary",
        )
    )

    # --------------------------------------------------------
    # Source URL
    # --------------------------------------------------------

    source_url = (
        extract_field(
            text,
            "Official Source URL",
        )
        or extract_field(
            text,
            "Official Source",
        )
        or extract_field(
            text,
            "Source URL",
        )
        or extract_field(
            text,
            "Source",
        )
        or extract_field(
            text,
            "Website",
        )
        or extract_field(
            text,
            "Official Website",
        )
        or extract_field(
            text,
            "Official URL",
        )
        or extract_field(
            text,
            "URL",
        )
        or extract_field(
            text,
            "source_url",
        )
    )

    # If no labelled URL exists, inspect the document.
    if not source_url:

        source_url = (
            extract_url_from_text(
                text
            )
        )

    # --------------------------------------------------------
    # Benefit
    # --------------------------------------------------------

    benefit = (
        extract_field(
            text,
            "Benefit",
        )
        or extract_field(
            text,
            "Benefit Description",
        )
        or extract_field(
            text,
            "Benefits",
        )
    )

    # --------------------------------------------------------
    # Resolve state
    # --------------------------------------------------------

    if is_invalid_scheme_id(
        state
    ):

        parent_name = (
            file_path.parent.name
            .strip()
            .lower()
        )

        if parent_name == "andhra_pradesh":

            state = "andhra pradesh"

        elif parent_name == "telangana":

            state = "telangana"

    # --------------------------------------------------------
    # Resolve scheme name
    # --------------------------------------------------------

    if not is_invalid_scheme_id(
        official_name
    ):

        resolved_scheme_name = (
            official_name
        )

    elif not is_invalid_scheme_id(
        scheme_name
    ):

        resolved_scheme_name = (
            scheme_name
        )

    else:

        resolved_scheme_name = (
            clean_filename_stem(
                file_path
            )
        )

    # --------------------------------------------------------
    # Scheme ID
    # --------------------------------------------------------

    if is_invalid_scheme_id(
        scheme_id
    ):

        scheme_id = fallback_scheme_id(
            resolved_scheme_name,
            state,
            government_level,
            file_path,
        )

    else:

        scheme_id = normalize_scheme_id(
            scheme_id
        )

        # Defensive protection against
        # normalized placeholders.
        if (
            not scheme_id
            or is_invalid_scheme_id(
                scheme_id
            )
            or scheme_id
            == "NOT_SPECIFIED_IN_THE_VERIFIED_SOURCE"
        ):

            scheme_id = fallback_scheme_id(
                resolved_scheme_name,
                state,
                government_level,
                file_path,
            )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    if is_invalid_scheme_id(
        scheme_id
    ):

        raise ValueError(
            "Could not generate valid scheme ID "
            f"for: {file_path}"
        )

    return {
        "scheme_id":
            scheme_id,

        "scheme_name":
            resolved_scheme_name,

        "government_level":
            government_level,

        "state": (
            state.lower()
            if state
            else None
        ),

        "ministry_department":
            department,

        "category":
            category,

        "subcategory":
            subcategory,

        "target_beneficiary":
            target,

        "scheme_status":
            status,

        "benefit_description":
            benefit,

        "source_url":
            source_url,
    }


# ============================================================
# CHUNKING
# ============================================================

def split_text(
    text: str,
):
    """
    Character-based chunking.

    Attempts to split on paragraph/sentence boundaries.
    """

    text = clean_text(
        text
    )

    if len(text) <= CHUNK_SIZE:

        return [text]

    chunks = []

    start = 0

    while start < len(text):

        end = min(
            start + CHUNK_SIZE,
            len(text),
        )

        chunk = text[
            start:end
        ]

        if end < len(text):

            last_break = max(
                chunk.rfind(
                    "\n\n"
                ),
                chunk.rfind(
                    ". "
                ),
                chunk.rfind(
                    "। "
                ),
            )

            if (
                last_break
                > CHUNK_SIZE * 0.55
            ):

                end = (
                    start
                    + last_break
                    + 1
                )

                chunk = text[
                    start:end
                ]

        chunks.append(
            chunk.strip()
        )

        if end >= len(text):

            break

        start = max(
            end - CHUNK_OVERLAP,
            start + 1,
        )

    return chunks


# ============================================================
# DOCUMENT PARSER
# ============================================================

def parse_markdown_file(
    file_path: Path,
    government_level: str,
):

    raw_text = file_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    text = clean_text(
        raw_text
    )

    metadata = get_metadata(
        text,
        file_path,
        government_level,
    )

    # Never allow placeholder IDs
    # to reach chunk generation.
    if is_invalid_scheme_id(
        metadata.get(
            "scheme_id"
        )
    ):

        raise ValueError(
            "Failed to resolve valid scheme_id "
            f"for source file: {file_path}"
        )

    chunks = split_text(
        text
    )

    records = []

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):

        # ----------------------------------------------------
        # Unique chunk ID
        # ----------------------------------------------------

        chunk_id = (
            f"{metadata['scheme_id']}"
            f"_c{index}"
        )

        # ----------------------------------------------------
        # Eligibility
        # ----------------------------------------------------

        eligibility_rules = (
            build_eligibility_rules(
                text,
                file_path.name,
                chunk_id,
            )
        )

        # ----------------------------------------------------
        # Exclusions
        # ----------------------------------------------------

        exclusion_rules = (
            build_exclusion_rules(
                text,
                file_path.name,
                chunk_id,
            )
        )

        # ----------------------------------------------------
        # Record
        # ----------------------------------------------------

        record = {

            "chunk_id":
                chunk_id,

            "scheme_id":
                metadata["scheme_id"],

            "scheme_name":
                metadata["scheme_name"],

            "government_level":
                metadata[
                    "government_level"
                ],

            "state":
                metadata["state"],

            "ministry_department":
                metadata[
                    "ministry_department"
                ],

            "category":
                metadata["category"],

            "subcategory":
                metadata["subcategory"],

            "target_beneficiary":
                metadata[
                    "target_beneficiary"
                ],

            "scheme_status":
                metadata[
                    "scheme_status"
                ],

            "benefit_description":
                metadata[
                    "benefit_description"
                ],

            "eligibility_rules":
                eligibility_rules,

            "exclusion_rules":
                exclusion_rules,

            # This dataset contains structured source
            # documents. Do not claim independent verification.
            "verification_status":
                "SOURCE_DOCUMENT_STRUCTURED",

            "source_url":
                metadata[
                    "source_url"
                ],

            "source_status":
                "SOURCE_DOCUMENT_STRUCTURED",

            "source_file":
                file_path.name,

            "document_title":
                metadata[
                    "scheme_name"
                ],

            "page_number":
                None,

            "chunk_number":
                index,

            "text":
                chunk,
        }

        records.append(
            record
        )

    return records


# ============================================================
# FILE DISCOVERY
# ============================================================

def discover_ap_files():

    if not AP_DIR.exists():

        raise FileNotFoundError(
            "Andhra Pradesh directory not found:\n"
            f"{AP_DIR}"
        )

    return sorted(
        [
            p
            for p in AP_DIR.iterdir()
            if (
                p.is_file()
                and p.name.lower().endswith(
                    ".md.txt"
                )
            )
        ]
    )


def discover_telangana_files():

    if not TG_DIR.exists():

        raise FileNotFoundError(
            "Telangana directory not found:\n"
            f"{TG_DIR}"
        )

    return sorted(
        [
            p
            for p in TG_DIR.iterdir()
            if (
                p.is_file()
                and p.suffix.lower() == ".md"
            )
        ]
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_record(
    record,
):

    missing = [
        key
        for key in EXPECTED_KEYS
        if key not in record
    ]

    if missing:

        raise ValueError(
            "Missing keys in "
            f"{record.get('chunk_id')}: "
            f"{missing}"
        )

    extra = [
        key
        for key in record
        if key not in EXPECTED_KEYS
    ]

    if extra:

        raise ValueError(
            "Unexpected keys in "
            f"{record.get('chunk_id')}: "
            f"{extra}"
        )


def validate_dataset(
    records,
):

    # --------------------------------------------------------
    # Schema validation
    # --------------------------------------------------------

    for record in records:

        validate_record(
            record
        )

    # --------------------------------------------------------
    # Chunk ID validation
    # --------------------------------------------------------

    chunk_ids = [
        record["chunk_id"]
        for record in records
    ]

    counts = {}

    for chunk_id in chunk_ids:

        counts[chunk_id] = (
            counts.get(
                chunk_id,
                0,
            )
            + 1
        )

    duplicates = {
        chunk_id: count
        for chunk_id, count
        in counts.items()
        if count > 1
    }

    if duplicates:

        raise ValueError(
            "Duplicate chunk IDs detected: "
            f"{duplicates}"
        )

    # --------------------------------------------------------
    # Scheme ID validation
    # --------------------------------------------------------

    invalid_ids = []

    for record in records:

        scheme_id = record.get(
            "scheme_id"
        )

        if is_invalid_scheme_id(
            scheme_id
        ):

            invalid_ids.append(
                (
                    record["chunk_id"],
                    scheme_id,
                )
            )

    if invalid_ids:

        raise ValueError(
            "Invalid scheme IDs detected: "
            f"{invalid_ids[:20]}"
        )

    # --------------------------------------------------------
    # Scheme name validation
    # --------------------------------------------------------

    invalid_names = []

    for record in records:

        scheme_name = record.get(
            "scheme_name"
        )

        if is_invalid_scheme_id(
            scheme_name
        ):

            invalid_names.append(
                (
                    record["chunk_id"],
                    scheme_name,
                )
            )

    if invalid_names:

        raise ValueError(
            "Invalid scheme names detected: "
            f"{invalid_names[:20]}"
        )

    # --------------------------------------------------------
    # Text validation
    # --------------------------------------------------------

    empty_text = [
        record["chunk_id"]
        for record in records
        if not record.get(
            "text"
        )
        or not record[
            "text"
        ].strip()
    ]

    if empty_text:

        raise ValueError(
            "Empty text chunks detected: "
            f"{empty_text[:20]}"
        )

    print(
        f"VALIDATION PASSED: "
        f"{len(records)} records"
    )


# ============================================================
# SOURCE SUMMARY
# ============================================================

def print_dataset_summary(
    records,
    title="DATASET SUMMARY",
):

    print()

    print("=" * 70)

    print(title)

    print("=" * 70)

    government_levels = {}

    states = {}

    schemes = set()

    for record in records:

        level = record.get(
            "government_level"
        )

        government_levels[level] = (
            government_levels.get(
                level,
                0,
            )
            + 1
        )

        state = record.get(
            "state"
        )

        states[state] = (
            states.get(
                state,
                0,
            )
            + 1
        )

        schemes.add(
            record.get(
                "scheme_id"
            )
        )

    print(
        f"Total chunks       : "
        f"{len(records)}"
    )

    print(
        f"Unique schemes     : "
        f"{len(schemes)}"
    )

    print(
        f"Government levels  : "
        f"{government_levels}"
    )

    print(
        f"States             : "
        f"{states}"
    )


# ============================================================
# METADATA QUALITY REPORT
# ============================================================

def print_state_quality_report(
    records,
):

    state_records = [
        record
        for record in records
        if record.get(
            "government_level"
        ) == "state"
    ]

    if not state_records:

        return

    print()
    print("=" * 70)
    print(
        "STATE METADATA QUALITY REPORT"
    )
    print("=" * 70)

    ap_records = [
        record
        for record in state_records
        if record.get(
            "state"
        ) == "andhra pradesh"
    ]

    tg_records = [
        record
        for record in state_records
        if record.get(
            "state"
        ) == "telangana"
    ]

    print(
        f"AP records                 : "
        f"{len(ap_records)}"
    )

    print(
        f"Telangana records          : "
        f"{len(tg_records)}"
    )

    print(
        f"AP missing eligibility     : "
        f"{sum(not r.get('eligibility_rules') for r in ap_records)}"
    )

    print(
        f"TG missing eligibility     : "
        f"{sum(not r.get('eligibility_rules') for r in tg_records)}"
    )

    print(
        f"AP missing source URL      : "
        f"{sum(not r.get('source_url') for r in ap_records)}"
    )

    print(
        f"TG missing source URL      : "
        f"{sum(not r.get('source_url') for r in tg_records)}"
    )

    print(
        f"State missing status       : "
        f"{sum(not r.get('scheme_status') for r in state_records)}"
    )


# ============================================================
# MAIN BUILDER
# ============================================================

def main():

    print("=" * 70)

    print(
        "MULTILINGUAL RAG - "
        "UNIFIED DATASET BUILDER"
    )

    print("=" * 70)

    # --------------------------------------------------------
    # Load existing unified dataset
    # --------------------------------------------------------

    if not UNIFIED_FILE.exists():

        raise FileNotFoundError(
            "Existing unified dataset not found:\n"
            f"{UNIFIED_FILE}"
        )

    with open(
        UNIFIED_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        existing_records = json.load(
            f
        )

    print(
        f"\nExisting records loaded: "
        f"{len(existing_records)}"
    )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # The current rag_documents.json contains the original
    # Central dataset plus previously generated AP/Telangana
    # records.
    #
    # We must NOT append AP/Telangana to the already-expanded
    # dataset, otherwise every run would duplicate them.
    #
    # Therefore keep only the original Central records here.
    # --------------------------------------------------------

    if not isinstance(
        existing_records,
        list,
    ):

        raise ValueError(
            "rag_documents.json must "
            "contain a list."
        )

    central_records = [
        record
        for record in existing_records
        if record.get(
            "government_level"
        ) == "central"
    ]

    # --------------------------------------------------------
    # Preserve Central dataset exactly
    # --------------------------------------------------------

    if len(central_records) != 1109:

        raise ValueError(
            "Expected exactly 1109 Central "
            "records, but found "
            f"{len(central_records)}."
        )

    print(
        f"Central records retained: "
        f"{len(central_records)}"
    )

    validate_dataset(
        central_records
    )

    central_count_before = len(
        central_records
    )

    # --------------------------------------------------------
    # Discover AP
    # --------------------------------------------------------

    ap_files = discover_ap_files()

    print(
        f"\nAndhra Pradesh source files: "
        f"{len(ap_files)}"
    )

    for path in ap_files:

        print(
            f"  AP: {path.name}"
        )

    # --------------------------------------------------------
    # Discover Telangana
    # --------------------------------------------------------

    tg_files = discover_telangana_files()

    print(
        f"\nTelangana primary Markdown "
        f"files: {len(tg_files)}"
    )

    for path in tg_files:

        print(
            f"  TG: {path.name}"
        )

    # --------------------------------------------------------
    # Parse AP
    # --------------------------------------------------------

    new_records = []

    for path in ap_files:

        print(
            f"\nProcessing AP: "
            f"{path.name}"
        )

        records = parse_markdown_file(
            path,
            government_level="state",
        )

        new_records.extend(
            records
        )

        print(
            f"  Generated chunks: "
            f"{len(records)}"
        )

    # --------------------------------------------------------
    # Parse Telangana
    # --------------------------------------------------------

    for path in tg_files:

        print(
            f"\nProcessing Telangana: "
            f"{path.name}"
        )

        records = parse_markdown_file(
            path,
            government_level="state",
        )

        new_records.extend(
            records
        )

        print(
            f"  Generated chunks: "
            f"{len(records)}"
        )

    # --------------------------------------------------------
    # Show resolved IDs
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print(
        "RESOLVED AP/TELANGANA SCHEME IDS"
    )
    print("=" * 70)

    printed_scheme_ids = set()

    for record in new_records:

        scheme_id = record[
            "scheme_id"
        ]

        if scheme_id not in printed_scheme_ids:

            print(
                f"  {record['source_file']}"
                f" -> {scheme_id}"
            )

            printed_scheme_ids.add(
                scheme_id
            )

    # --------------------------------------------------------
    # Check duplicate chunk IDs
    # --------------------------------------------------------

    new_chunk_ids = [
        record["chunk_id"]
        for record in new_records
    ]

    new_counts = {}

    for chunk_id in new_chunk_ids:

        new_counts[chunk_id] = (
            new_counts.get(
                chunk_id,
                0,
            )
            + 1
        )

    internal_duplicates = {
        chunk_id: count
        for chunk_id, count
        in new_counts.items()
        if count > 1
    }

    if internal_duplicates:

        raise ValueError(
            "Duplicate IDs found within "
            "AP/Telangana records:\n"
            f"{internal_duplicates}"
        )

    # --------------------------------------------------------
    # Ensure scheme IDs are not shared by
    # different source files
    # --------------------------------------------------------

    scheme_sources = {}

    for record in new_records:

        scheme_id = record[
            "scheme_id"
        ]

        source_file = record[
            "source_file"
        ]

        scheme_sources.setdefault(
            scheme_id,
            set(),
        ).add(
            source_file
        )

    conflicting_scheme_ids = {
        scheme_id: sorted(
            source_files
        )
        for scheme_id, source_files
        in scheme_sources.items()
        if len(source_files) > 1
    }

    if conflicting_scheme_ids:

        raise ValueError(
            "The same scheme_id was generated "
            "for multiple AP/Telangana source files:\n"
            f"{conflicting_scheme_ids}"
        )

    # --------------------------------------------------------
    # Deduplicate against Central
    # --------------------------------------------------------

    existing_ids = {
        record["chunk_id"]
        for record in central_records
    }

    filtered_records = []

    skipped_duplicates = []

    for record in new_records:

        if record["chunk_id"] in existing_ids:

            skipped_duplicates.append(
                record["chunk_id"]
            )

            print(
                "Skipping duplicate: "
                f"{record['chunk_id']}"
            )

            continue

        filtered_records.append(
            record
        )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    combined = (
        central_records
        + filtered_records
    )

    # --------------------------------------------------------
    # Verify Central records preserved
    # --------------------------------------------------------

    combined_central = [
        record
        for record in combined
        if record.get(
            "government_level"
        ) == "central"
    ]

    if (
        len(combined_central)
        != central_count_before
    ):

        raise ValueError(
            "Central record count changed! "
            f"Before: {central_count_before}, "
            f"After: {len(combined_central)}"
        )

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    validate_dataset(
        combined
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    UNIFIED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        UNIFIED_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            combined,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # --------------------------------------------------------
    # Final statistics
    # --------------------------------------------------------

    central_count = len(
        central_records
    )

    added_count = len(
        filtered_records
    )

    total_count = len(
        combined
    )

    unique_schemes = len(
        {
            record["scheme_id"]
            for record in combined
        }
    )

    print()
    print("=" * 70)

    print(
        "UNIFIED DATASET COMPLETE"
    )

    print("=" * 70)

    print(
        f"Central records preserved : "
        f"{central_count}"
    )

    print(
        f"New AP/Telangana records : "
        f"{added_count}"
    )

    print(
        f"Total unified records     : "
        f"{total_count}"
    )

    print(
        f"Unique schemes            : "
        f"{unique_schemes}"
    )

    print(
        f"Duplicates skipped        : "
        f"{len(skipped_duplicates)}"
    )

    print()
    print(
        "Output:"
    )

    print(
        UNIFIED_FILE
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print_dataset_summary(
        combined,
        "FINAL UNIFIED DATASET SUMMARY",
    )

    # --------------------------------------------------------
    # State quality report
    # --------------------------------------------------------

    print_state_quality_report(
        combined
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()