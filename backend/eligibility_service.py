from __future__ import annotations

from typing import Any, Dict, List, Optional
import re

from backend.profile_mapper import extract_profile, compact_profile
from backend.discovery_search import discover_schemes
from backend.rule_evaluator import evaluate_scheme_rules
from backend.question_generator import generate_questions


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_RETRIEVAL_TOP_K = 60
DEFAULT_MAX_SCHEMES = 10
MAX_NEXT_QUESTIONS = 3
MIN_RELEVANCE_SCORE = 0.18


# ============================================================
# STATUS PRIORITY
# ============================================================

STATUS_PRIORITY = {
    "ELIGIBLE": 1,
    "NEED_MORE_INFORMATION": 2,
    "NOT_ELIGIBLE": 3,
    "RULES_REQUIRE_REVIEW": 4,
    "CURRENT_STATUS_UNCONFIRMED": 5,
    "HISTORICAL_OR_PROPOSED": 6,
    "NO_RELEVANT_SCHEME": 99,
}


# ============================================================
# TOPIC KEYWORDS
# ============================================================

TOPIC_KEYWORDS = {

    "scholarship": [
        "scholarship",
        "scholarships",
        "student",
        "students",
        "education",
        "educational",
        "college",
        "university",
        "school",
        "study",
        "studying",
        "tuition",
        "fee reimbursement",
        "fee",
        "post matric",
        "pre matric",
        "overseas education",

        # Telugu
        "స్కాలర్‌షిప్",
        "స్కాలర్షిప్",
        "స్కాలర్ షిప్",
        "విద్యార్థి",
        "విద్యార్థులు",
        "విద్య",
        "చదువు",
        "కాలేజీ",
        "కళాశాల",
        "యూనివర్సిటీ",
        "పాఠశాల",
        "ఫీజు",
        "ఫీజు రీయింబర్స్‌మెంట్",
    ],

    "agriculture": [
        "farmer",
        "farmers",
        "farming",
        "agriculture",
        "agricultural",
        "cultivation",
        "crop",
        "crops",
        "land",
        "farmland",
        "tenant farmer",
        "cultivator",
        "kisan",
        "rythu",

        # Telugu
        "కిసాన్",
        "రైతు",
        "రైతులు",
        "వ్యవసాయం",
        "పంట",
        "పంటలు",
        "సాగు",
        "వ్యవసాయ భూమి",
    ],

    "housing": [
        "house",
        "housing",
        "home",
        "home loan",
        "construction",
        "pucca house",
        "shelter",
        "housing assistance",

        # Telugu
        "ఇల్లు",
        "ఇంటి",
        "గృహ",
        "గృహం",
        "గృహ నిర్మాణం",
        "ఇంటి నిర్మాణం",
        "ఇంటి పథకం",
    ],

    "health": [
        "health",
        "medical",
        "medicine",
        "hospital",
        "treatment",
        "health insurance",
        "hospitalization",
        "disease",
        "surgery",
        "aarogyasri",
        "ayushman",

        # Telugu
        "ఆరోగ్యం",
        "ఆరోగ్య",
        "వైద్యం",
        "ఆసుపత్రి",
        "చికిత్స",
        "ఆరోగ్యశ్రీ",
    ],

    "pension": [
        "pension",
        "pensions",
        "senior citizen",
        "old age",
        "widow",
        "widows",
        "disability pension",
        "social security",

        # Telugu
        "పెన్షన్",
        "పింఛన్",
        "వృద్ధాప్య",
        "వృద్ధులు",
        "వితంతువు",
        "వితంతువులు",
        "దివ్యాంగ",
    ],

    "women": [
        "woman",
        "women",
        "girl",
        "girls",
        "female",
        "mother",
        "widow",
        "women empowerment",
        "marriage assistance",

        # Telugu
        "మహిళ",
        "మహిళలు",
        "స్త్రీ",
        "స్త్రీలు",
        "బాలిక",
        "బాలికలు",
        "తల్లి",
    ],

    "employment": [
        "employment",
        "job",
        "jobs",
        "unemployed",
        "unemployment",
        "worker",
        "workers",
        "skill",
        "training",
        "livelihood",
        "employment assistance",

        # Telugu
        "ఉద్యోగం",
        "ఉద్యోగాలు",
        "నిరుద్యోగి",
        "నిరుద్యోగం",
        "ఉపాధి",
        "కార్మికుడు",
        "కార్మికులు",
        "నైపుణ్యం",
    ],

    "business": [
        "business",
        "entrepreneur",
        "entrepreneurship",
        "startup",
        "enterprise",
        "loan",
        "credit",
        "mudra",
        "self employment",
        "small business",

        # Telugu
        "వ్యాపారం",
        "వ్యాపారి",
        "వ్యవసాయేతర వ్యాపారం",
        "రుణం",
        "లోన్",
        "క్రెడిట్",
        "స్వయం ఉపాధి",
    ],

    "food": [
        "food",
        "ration",
        "rice",
        "grain",
        "nutrition",
        "meal",
        "midday meal",
        "food security",

        # Telugu
        "ఆహారం",
        "రేషన్",
        "బియ్యం",
        "ధాన్యం",
        "పోషణ",
        "భోజనం",
    ],

    "disability": [
        "disabled",
        "disability",
        "divyang",
        "pwd",
        "differently abled",
        "disability certificate",

        # Telugu
        "దివ్యాంగ",
        "వికలాంగ",
        "వైకల్యం",
    ],

    "child": [
        "child",
        "children",
        "child welfare",
        "girl child",
        "boy child",
        "student",

        # Telugu
        "పిల్ల",
        "పిల్లలు",
        "బాలుడు",
        "బాలిక",
        "శిశువు",
    ],
}


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(value: Any) -> str:
    """Safely normalize a value to searchable text."""

    if value is None:
        return ""

    text = str(value).lower().strip()
    text = re.sub(r"\s+", " ", text)

    return text


# ============================================================
# LANGUAGE DETECTION
# ============================================================

def detect_response_language(query: str) -> str:
    """
    Detect the preferred user-facing response language.

    Returns:
        telugu  -> Telugu-dominant query
        english -> English-dominant query
        mixed   -> Mixed query where Telugu is significant

    For final UI generation, mixed queries are treated as Telugu
    when Telugu characters are sufficiently present.
    """

    query = (query or "").strip()

    if not query:
        return "english"

    telugu_chars = sum(
        1
        for ch in query
        if "\u0C00" <= ch <= "\u0C7F"
    )

    english_chars = sum(
        1
        for ch in query
        if ch.isascii() and ch.isalpha()
    )

    if telugu_chars == 0:
        return "english"

    if english_chars == 0:
        return "telugu"

    if telugu_chars >= english_chars * 0.25:
        return "telugu"

    return "english"


# ============================================================
# TOPIC DETECTION
# ============================================================

def _detect_topics(
    query: str,
    discovery: Optional[Dict[str, Any]] = None,
) -> List[str]:

    topics: List[str] = []

    # Prefer topics already detected by discovery_search.
    if discovery:
        discovered_topics = discovery.get("topics", [])

        if discovered_topics:
            for topic in discovered_topics:
                topic = str(topic).strip().lower()

                if topic and topic not in topics:
                    topics.append(topic)

    normalized_query = _normalize(query)

    for topic, keywords in TOPIC_KEYWORDS.items():

        for keyword in keywords:

            normalized_keyword = _normalize(keyword)

            if not normalized_keyword:
                continue

            if normalized_keyword in normalized_query:

                if topic not in topics:
                    topics.append(topic)

                break

    return topics


# ============================================================
# SCHEME TEXT
# ============================================================

def _scheme_search_text(
    scheme: Dict[str, Any]
) -> str:

    fields = [
        scheme.get("scheme_name"),
        scheme.get("category"),
        scheme.get("subcategory"),
        scheme.get("target_beneficiary"),
        scheme.get("benefit_description"),
        scheme.get("eligibility_rules"),
        scheme.get("exclusion_rules"),
        scheme.get("government_level"),
        scheme.get("state"),
    ]

    parts: List[str] = []

    for field in fields:

        if field is None:
            continue

        if isinstance(field, list):

            for item in field:
                parts.append(_normalize(item))

        elif isinstance(field, dict):

            parts.append(_normalize(field))

        else:

            parts.append(_normalize(field))

    return " ".join(parts)


# ============================================================
# TOPIC SCORE
# ============================================================

def _topic_score(
    scheme: Dict[str, Any],
    topics: List[str],
) -> float:

    if not topics:
        return 0.0

    text = _scheme_search_text(scheme)

    if not text:
        return 0.0

    matched_topics = 0

    for topic in topics:

        keywords = TOPIC_KEYWORDS.get(topic, [])

        topic_match = False

        for keyword in keywords:

            if _normalize(keyword) in text:
                topic_match = True
                break

        if topic_match:
            matched_topics += 1

    return (
        matched_topics / len(topics)
        if topics
        else 0.0
    )


# ============================================================
# PROFILE RELEVANCE
# ============================================================

def _profile_relevance(
    scheme: Dict[str, Any],
    profile: Dict[str, Any],
) -> float:

    if not profile:
        return 0.0

    text = _scheme_search_text(scheme)

    if not text:
        return 0.0

    score = 0.0

    # Student
    if profile.get("student") is True:

        student_terms = [
            "student",
            "students",
            "education",
            "scholarship",
            "school",
            "college",
            "university",
            "విద్యార్థి",
            "విద్య",
            "స్కాలర్",
        ]

        if any(
            _normalize(term) in text
            for term in student_terms
        ):
            score += 0.25

    # Farmer
    if (
        profile.get("landholder") is True
        or profile.get("tenant_farmer") is True
        or profile.get("landless") is True
    ):

        farmer_terms = [
            "farmer",
            "farmers",
            "agriculture",
            "agricultural",
            "cultivator",
            "kisan",
            "rythu",
            "రైతు",
            "వ్యవసాయం",
            "కిసాన్",
        ]

        if any(
            _normalize(term) in text
            for term in farmer_terms
        ):
            score += 0.25

    # Unemployed
    if profile.get("employment_status") == "unemployed":

        employment_terms = [
            "employment",
            "unemployment",
            "job",
            "worker",
            "livelihood",
            "skill",
            "training",
            "నిరుద్యోగ",
            "ఉద్యోగం",
            "ఉపాధి",
        ]

        if any(
            _normalize(term) in text
            for term in employment_terms
        ):
            score += 0.25

    # Disability
    if profile.get("disability") is True:

        disability_terms = [
            "disability",
            "disabled",
            "divyang",
            "pwd",
            "దివ్యాంగ",
            "వికలాంగ",
            "వైకల్యం",
        ]

        if any(
            _normalize(term) in text
            for term in disability_terms
        ):
            score += 0.25

    # Government employee
    if profile.get("government_employee") is True:

        if "government" in text:
            score += 0.05

    return min(score, 1.0)


# ============================================================
# RELEVANCE
# ============================================================

def _calculate_relevance(
    scheme: Dict[str, Any],
    topics: List[str],
    profile: Dict[str, Any],
) -> float:

    retrieval_score = float(
        scheme.get("final_score", 0.0) or 0.0
    )

    topic_score = _topic_score(
        scheme,
        topics,
    )

    beneficiary_score = _profile_relevance(
        scheme,
        profile,
    )

    combined = (
        retrieval_score * 0.55
        + topic_score * 0.30
        + beneficiary_score * 0.15
    )

    return round(combined, 6)


# ============================================================
# STATUS HELPERS
# ============================================================

def _status_text(
    scheme: Dict[str, Any]
) -> str:

    return _normalize(
        scheme.get("scheme_status")
    )


def _is_historical_or_proposed(
    scheme: Dict[str, Any]
) -> bool:

    status = _status_text(scheme)

    historical_markers = [
        "historical",
        "proposed",
        "under review",
        "unconfirmed",
        "discontinued",
        "closed",
        "legacy",
    ]

    return any(
        marker in status
        for marker in historical_markers
    )


def _is_current_status_confirmed(
    scheme: Dict[str, Any]
) -> bool:

    status = _status_text(scheme)

    if not status:
        return True

    current_markers = [
        "active_current",
        "active",
        "current",
        "ongoing",
        "operational",
    ]

    return any(
        marker in status
        for marker in current_markers
    )


# ============================================================
# CANDIDATE SELECTION
# ============================================================

def _select_candidate_schemes(
    schemes: List[Dict[str, Any]],
    query: str,
    profile: Dict[str, Any],
    topics: List[str],
    detected_scheme: Optional[str],
    max_schemes: int,
) -> List[Dict[str, Any]]:

    if not schemes:
        return []

    # --------------------------------------------------------
    # Explicit scheme
    # --------------------------------------------------------

    if detected_scheme:

        exact_matches = []

        for scheme in schemes:

            if scheme.get("scheme_id") == detected_scheme:
                exact_matches.append(scheme)

        # Never evaluate unrelated fallback schemes when
        # the router explicitly detected a scheme.
        return exact_matches[:max_schemes]

    # --------------------------------------------------------
    # Topic filtering
    # --------------------------------------------------------

    candidates = []

    for scheme in schemes:

        topic_score = _topic_score(
            scheme,
            topics,
        )

        beneficiary_score = _profile_relevance(
            scheme,
            profile,
        )

        relevance = _calculate_relevance(
            scheme,
            topics,
            profile,
        )

        item = dict(scheme)

        item["_topic_score"] = topic_score
        item["_beneficiary_score"] = beneficiary_score
        item["_eligibility_relevance"] = relevance

        # If a topic exists, the scheme must actually match it.
        if topics:

            if topic_score <= 0:
                continue

            if relevance < MIN_RELEVANCE_SCORE:
                continue

        else:

            if relevance < MIN_RELEVANCE_SCORE:
                continue

        candidates.append(item)

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    candidates.sort(
        key=lambda item: (
            item.get("_topic_score", 0.0),
            item.get("_eligibility_relevance", 0.0),
            item.get("_beneficiary_score", 0.0),
            item.get("final_score", 0.0),
        ),
        reverse=True,
    )

    return candidates[:max_schemes]


# ============================================================
# MISSING INFORMATION
# ============================================================

def _collect_missing_information(
    evaluation: Dict[str, Any]
) -> List[str]:

    missing: List[str] = []

    for result in evaluation.get(
        "rule_results",
        []
    ):

        if result.get("status") != "UNKNOWN":
            continue

        field = result.get("field")

        if field and field not in missing:
            missing.append(field)

    return missing


# ============================================================
# FAILED RULES
# ============================================================

def _collect_failed_rules(
    evaluation: Dict[str, Any]
) -> List[Dict[str, Any]]:

    failed = []

    for result in evaluation.get(
        "rule_results",
        []
    ):

        if result.get("status") == "FAIL":
            failed.append(result)

    return failed


# ============================================================
# UNSUPPORTED RULES
# ============================================================

def _collect_unsupported_rules(
    evaluation: Dict[str, Any]
) -> List[Dict[str, Any]]:

    unsupported = []

    for result in evaluation.get(
        "rule_results",
        []
    ):

        if result.get("status") == "UNSUPPORTED":
            unsupported.append(result)

    return unsupported


# ============================================================
# SCHEME RESULT
# ============================================================

def _scheme_result(
    scheme: Dict[str, Any],
    evaluation: Dict[str, Any],
) -> Dict[str, Any]:

    missing_fields = _collect_missing_information(
        evaluation
    )

    failed_rules = _collect_failed_rules(
        evaluation
    )

    unsupported_rules = _collect_unsupported_rules(
        evaluation
    )

    questions = []

    if evaluation.get("status") == "NEED_MORE_INFORMATION":

        questions = generate_questions(
            evaluation,
            max_questions=MAX_NEXT_QUESTIONS,
        )

    return {
        # Identity
        "scheme_id": scheme.get("scheme_id"),
        "scheme_name": scheme.get("scheme_name"),

        # Geography
        "government_level": scheme.get(
            "government_level"
        ),
        "state": scheme.get("state"),

        # Classification
        "category": scheme.get("category"),
        "subcategory": scheme.get("subcategory"),
        "target_beneficiary": scheme.get(
            "target_beneficiary"
        ),

        # Status
        "scheme_status": scheme.get(
            "scheme_status"
        ),
        "verification_status": scheme.get(
            "verification_status"
        ),
        "source_status": scheme.get(
            "source_status"
        ),

        # Benefits and rules
        "benefit_description": scheme.get(
            "benefit_description"
        ),
        "eligibility_rules": scheme.get(
            "eligibility_rules"
        ),
        "exclusion_rules": scheme.get(
            "exclusion_rules"
        ),

        # Sources
        "source_url": scheme.get("source_url"),
        "source_file": scheme.get("source_file"),
        "document_title": scheme.get(
            "document_title"
        ),

        # Evaluation
        "evaluation": evaluation,
        "status": evaluation.get("status"),

        "missing_fields": missing_fields,
        "failed_rules": failed_rules,
        "unsupported_rules": unsupported_rules,
        "questions": questions,

        # Retrieval
        "score": scheme.get("final_score"),

        "eligibility_relevance": scheme.get(
            "_eligibility_relevance"
        ),

        "topic_score": scheme.get(
            "_topic_score"
        ),

        "beneficiary_score": scheme.get(
            "_beneficiary_score"
        ),

        # Status flags
        "current_status_confirmed": (
            _is_current_status_confirmed(
                scheme
            )
        ),

        "historical_or_proposed": (
            _is_historical_or_proposed(
                scheme
            )
        ),
    }


# ============================================================
# RESULT SORTING
# ============================================================

def _sort_results(
    results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    return sorted(
        results,
        key=lambda x: (
            STATUS_PRIORITY.get(
                x.get("status"),
                99,
            ),
            -(
                x.get(
                    "eligibility_relevance",
                    x.get("score", 0.0),
                )
                or 0.0
            ),
        ),
    )


# ============================================================
# NEXT QUESTIONS
# ============================================================

def _select_next_questions(
    evaluated_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    # Prefer questions from the highest-priority
    # unresolved scheme.

    for result in evaluated_results:

        if result.get(
            "status"
        ) != "NEED_MORE_INFORMATION":
            continue

        questions = result.get(
            "questions",
            [],
        )

        if questions:
            return questions[:MAX_NEXT_QUESTIONS]

    return []


# ============================================================
# OVERALL STATUS
# ============================================================

def _calculate_overall_status(
    evaluated_results: List[Dict[str, Any]]
) -> str:

    if not evaluated_results:
        return "NO_RELEVANT_SCHEME"

    statuses = [
        result.get("status")
        for result in evaluated_results
    ]

    # Conservative rule:
    # If any relevant scheme still needs information,
    # do not claim overall eligibility yet.
    if "NEED_MORE_INFORMATION" in statuses:
        return "NEED_MORE_INFORMATION"

    if "ELIGIBLE" in statuses:
        return "ELIGIBLE"

    if "NOT_ELIGIBLE" in statuses:
        return "NOT_ELIGIBLE"

    if "RULES_REQUIRE_REVIEW" in statuses:
        return "RULES_REQUIRE_REVIEW"

    if "CURRENT_STATUS_UNCONFIRMED" in statuses:
        return "CURRENT_STATUS_UNCONFIRMED"

    if "HISTORICAL_OR_PROPOSED" in statuses:
        return "HISTORICAL_OR_PROPOSED"

    return "NO_RELEVANT_SCHEME"

# ============================================================
# INFORMATION-ONLY RESULT
# ============================================================

def _build_information_result(
    scheme: Dict[str, Any],
    topics: List[str],
    profile: Dict[str, Any],
) -> Dict[str, Any]:

    item = dict(scheme)

    topic_score = _topic_score(
        scheme,
        topics,
    )

    beneficiary_score = _profile_relevance(
        scheme,
        profile,
    )

    relevance = _calculate_relevance(
        scheme,
        topics,
        profile,
    )

    if _is_historical_or_proposed(scheme):

        information_status = (
            "HISTORICAL_OR_PROPOSED"
        )

    elif not _is_current_status_confirmed(scheme):

        information_status = (
            "CURRENT_STATUS_UNCONFIRMED"
        )

    else:

        information_status = "INFORMATION_ONLY"

    return {
        "scheme_id": scheme.get("scheme_id"),
        "scheme_name": scheme.get("scheme_name"),

        "government_level": scheme.get(
            "government_level"
        ),

        "state": scheme.get("state"),

        "category": scheme.get("category"),

        "subcategory": scheme.get(
            "subcategory"
        ),

        "target_beneficiary": scheme.get(
            "target_beneficiary"
        ),

        "scheme_status": scheme.get(
            "scheme_status"
        ),

        "verification_status": scheme.get(
            "verification_status"
        ),

        "source_status": scheme.get(
            "source_status"
        ),

        "benefit_description": scheme.get(
            "benefit_description"
        ),

        "eligibility_rules": scheme.get(
            "eligibility_rules"
        ),

        "exclusion_rules": scheme.get(
            "exclusion_rules"
        ),

        "source_url": scheme.get(
            "source_url"
        ),

        "source_file": scheme.get(
            "source_file"
        ),

        "document_title": scheme.get(
            "document_title"
        ),

        # No eligibility decision.
        "status": information_status,
        "evaluation": None,
        "missing_fields": [],
        "failed_rules": [],
        "unsupported_rules": [],
        "questions": [],

        # Retrieval metadata.
        "score": scheme.get("final_score"),

        "eligibility_relevance": relevance,

        "topic_score": topic_score,

        "beneficiary_score": beneficiary_score,

        "current_status_confirmed": (
            _is_current_status_confirmed(
                scheme
            )
        ),

        "historical_or_proposed": (
            _is_historical_or_proposed(
                scheme
            )
        ),
    }


# ============================================================
# MAIN ELIGIBILITY SERVICE
# ============================================================

def check_eligibility(
    query: str,
    max_schemes: int = DEFAULT_MAX_SCHEMES,
) -> Dict[str, Any]:
    """
    Generic government-scheme eligibility workflow.

    Pipeline:

        USER QUERY
             |
             v
        Language detection
             |
             v
        Profile extraction
             |
             v
        Scheme discovery / RAG
             |
             v
        Intent detection
             |
             +----------------------+
             |                      |
             | ELIGIBILITY          |
             |                      |
             v                      v
        Candidate selection    Scheme information
             |                 / discovery
             v                      |
        Deterministic rules         |
             |                      |
             v                      |
        Missing information         |
             |                      |
             v                      |
        Questions                   |
             |                      |
             +----------+-----------+
                        |
                        v
                 Structured response

    IMPORTANT:
    The LLM is NOT used to make the eligibility decision.
    """

    # ========================================================
    # 1. Validate input
    # ========================================================

    query = (query or "").strip()

    response_language = detect_response_language(
        query
    )

    if not query:

        return {
            "query": query,
            "intent": None,
            "detected_state": None,
            "detected_scheme": None,
            "topics": [],
            "profile": {},
            "scope": {},
            "retrieved_chunks": 0,
            "overall_status": "NO_RELEVANT_SCHEME",
            "next_questions": [],
            "schemes_evaluated": 0,
            "schemes_found": 0,
            "results": [],
            "response_language": response_language,
            "message": (
                "Please provide a question about a "
                "government scheme or your eligibility."
            ),
        }

    # ========================================================
    # 2. Normalize max schemes
    # ========================================================

    try:
        max_schemes = int(max_schemes)

    except (TypeError, ValueError):

        max_schemes = DEFAULT_MAX_SCHEMES

    max_schemes = max(
        1,
        min(max_schemes, 20),
    )

    # ========================================================
    # 3. Extract profile
    # ========================================================

    profile = extract_profile(query)

    # --------------------------------------------------------
    # Important safeguard:
    #
    # "85%" is NOT automatically "85th percentile".
    #
    # If profile_mapper returns a percentage as percentile,
    # remove it unless the query explicitly says percentile.
    # --------------------------------------------------------

    normalized_query = query.lower()

    explicit_percentile = bool(
        re.search(
            r"\bpercentile\b",
            normalized_query,
            re.IGNORECASE,
        )
        or "పర్సెంటైల్" in query
    )

    explicit_percentage = bool(
        re.search(
            r"\b(?:percentage|percent|marks|%)\b",
            normalized_query,
            re.IGNORECASE,
        )
        or "%" in query
        or "మార్కులు" in query
    )

    if (
        explicit_percentage
        and not explicit_percentile
        and profile.get("class_12_percentile") is not None
    ):
        profile["class_12_percentile"] = None

    # ========================================================
    # 4. Discover schemes
    # ========================================================

    discovery = discover_schemes(
        query,
        top_k=DEFAULT_RETRIEVAL_TOP_K,
        final_count=max(
            max_schemes * 2,
            10,
        ),
    )

    schemes = discovery.get(
        "schemes",
        [],
    )

    # ========================================================
    # 5. Detection metadata
    # ========================================================

    intent = discovery.get(
        "intent"
    )

    detected_state = discovery.get(
        "detected_state"
    )

    detected_scheme = discovery.get(
        "detected_scheme"
    )

    topics = _detect_topics(
        query=query,
        discovery=discovery,
    )

    scope = discovery.get(
        "scope",
        {},
    )

    retrieved_chunks = discovery.get(
        "retrieved_chunks",
        0,
    )

    compacted_profile = compact_profile(
        profile
    )

    # ========================================================
    # 6. INFORMATION / DISCOVERY
    # ========================================================

    if intent in {
        "SCHEME_INFO",
        "SCHEME_DISCOVERY",
    }:

        info_results = []

        for scheme in schemes:

            item = _build_information_result(
                scheme=scheme,
                topics=topics,
                profile=profile,
            )

            info_results.append(item)

        # Information results are sorted by relevance,
        # not eligibility.
        info_results.sort(
            key=lambda x: (
                x.get(
                    "eligibility_relevance",
                    x.get("score", 0.0),
                )
                or 0.0
            ),
            reverse=True,
        )

        info_results = info_results[:max_schemes]

        if info_results:
            overall_status = "SCHEMES_FOUND"
        else:
            overall_status = "NO_RELEVANT_SCHEME"

        if intent == "SCHEME_DISCOVERY":

            if response_language == "telugu":

                message = (
                    "మీ అభ్యర్థనకు సంబంధించిన ప్రభుత్వ "
                    "పథకాలు ఇవి. ఇది పథక సమాచారం మాత్రమే; "
                    "అర్హతను నిర్ధారించలేదు."
                )

            else:

                message = (
                    "These government schemes are relevant "
                    "to your request. Eligibility has not "
                    "been determined because this is a "
                    "scheme-discovery query."
                )

        else:

            if response_language == "telugu":

                message = (
                    "మీ అభ్యర్థనకు సంబంధించిన ప్రభుత్వ "
                    "పథకాల సమాచారం ఇది. అర్హతను "
                    "నిర్ధారించలేదు."
                )

            else:

                message = (
                    "Here is information about the relevant "
                    "government schemes. Eligibility has not "
                    "been determined."
                )

        return {
            "query": query,

            "intent": intent,

            "detected_scheme": detected_scheme,

            "detected_state": detected_state,

            "topics": topics,

            "profile": compacted_profile,

            "scope": scope,

            "retrieved_chunks": retrieved_chunks,

            "overall_status": overall_status,

            "next_questions": [],

            "schemes_evaluated": 0,

            "schemes_found": len(
                info_results
            ),

            "results": info_results,

            "response_language": response_language,

            "message": message,
        }

    # ========================================================
    # 7. ELIGIBILITY CANDIDATES
    # ========================================================

    candidate_schemes = (
        _select_candidate_schemes(
            schemes=schemes,
            query=query,
            profile=profile,
            topics=topics,
            detected_scheme=detected_scheme,
            max_schemes=max_schemes,
        )
    )

    # ========================================================
    # 8. Deterministic rule evaluation
    # ========================================================

    evaluated_results: List[
        Dict[str, Any]
    ] = []

    for scheme in candidate_schemes:

        # ----------------------------------------------------
        # Historical / proposed schemes
        # ----------------------------------------------------

        if _is_historical_or_proposed(
            scheme
        ):

            result = {
                "scheme_id": scheme.get(
                    "scheme_id"
                ),

                "scheme_name": scheme.get(
                    "scheme_name"
                ),

                "government_level": scheme.get(
                    "government_level"
                ),

                "state": scheme.get("state"),

                "category": scheme.get(
                    "category"
                ),

                "subcategory": scheme.get(
                    "subcategory"
                ),

                "target_beneficiary": scheme.get(
                    "target_beneficiary"
                ),

                "scheme_status": scheme.get(
                    "scheme_status"
                ),

                "verification_status": scheme.get(
                    "verification_status"
                ),

                "source_status": scheme.get(
                    "source_status"
                ),

                "benefit_description": scheme.get(
                    "benefit_description"
                ),

                "eligibility_rules": scheme.get(
                    "eligibility_rules"
                ),

                "exclusion_rules": scheme.get(
                    "exclusion_rules"
                ),

                "source_url": scheme.get(
                    "source_url"
                ),

                "source_file": scheme.get(
                    "source_file"
                ),

                "document_title": scheme.get(
                    "document_title"
                ),

                "evaluation": {
                    "status": (
                        "RULES_REQUIRE_REVIEW"
                    ),

                    "reason": (
                        "The available dataset marks this "
                        "scheme as historical, proposed, "
                        "or current continuation unconfirmed. "
                        "A current eligibility decision should "
                        "not be inferred from historical rules."
                    ),

                    "rule_results": [],
                },

                "status": (
                    "RULES_REQUIRE_REVIEW"
                ),

                "missing_fields": [],

                "failed_rules": [],

                "unsupported_rules": [],

                "questions": [],

                "score": scheme.get(
                    "final_score"
                ),

                "eligibility_relevance": scheme.get(
                    "_eligibility_relevance"
                ),

                "topic_score": scheme.get(
                    "_topic_score"
                ),

                "beneficiary_score": scheme.get(
                    "_beneficiary_score"
                ),

                "current_status_confirmed": False,

                "historical_or_proposed": True,
            }

            evaluated_results.append(
                result
            )

            continue

        # ----------------------------------------------------
        # Current / usable scheme
        # ----------------------------------------------------

        evaluation = evaluate_scheme_rules(
            scheme,
            profile,
        )

        result = _scheme_result(
            scheme,
            evaluation,
        )

        evaluated_results.append(
            result
        )

    # ========================================================
    # 9. Sort
    # ========================================================

    evaluated_results = _sort_results(
        evaluated_results
    )

    # ========================================================
    # 10. Next questions
    # ========================================================

    next_questions = (
        _select_next_questions(
            evaluated_results
        )
    )

    # ========================================================
    # 11. Overall status
    # ========================================================

    overall_status = (
        _calculate_overall_status(
            evaluated_results
        )
    )

    # ========================================================
    # 12. User-facing message
    # ========================================================

    if response_language == "telugu":

        if overall_status == "ELIGIBLE":

            message = (
                "మీరు అందించిన వివరాల ఆధారంగా, "
                "పరిశీలించిన అర్హత నియమాల ప్రకారం "
                "ఈ పథకానికి అవసరమైన ప్రమాణాలు "
                "నెరవేరుతున్నాయి. తుది అర్హతను సంబంధిత "
                "ప్రభుత్వ శాఖ మాత్రమే నిర్ధారిస్తుంది."
            )

        elif overall_status == "NEED_MORE_INFORMATION":

            message = (
                "మీ వివరాలకు సరిపడే కొన్ని పథకాలు "
                "కనుగొనబడ్డాయి. అయితే అర్హతను "
                "నిర్ధారించడానికి మరికొన్ని వివరాలు "
                "అవసరం. క్రింద అడిగిన ప్రశ్నలకు "
                "సమాధానం ఇవ్వండి."
            )

        elif overall_status == "NOT_ELIGIBLE":

            message = (
                "మీరు అందించిన వివరాల ఆధారంగా, "
                "పరిశీలించిన పథకాలలో అవసరమైన కొన్ని "
                "అర్హత ప్రమాణాలు నెరవేరలేదు."
            )

        elif overall_status == "RULES_REQUIRE_REVIEW":

            message = (
                "సంబంధిత పథకాలు కనుగొనబడ్డాయి. అయితే "
                "అందుబాటులో ఉన్న ప్రభుత్వ నియమాల ఆధారంగా "
                "ప్రస్తుత అర్హతను ఖచ్చితంగా నిర్ధారించలేము."
            )

        else:

            message = (
                "మీ అభ్యర్థనకు సరిపడే ధృవీకరించదగిన "
                "పథకం కనుగొనబడలేదు."
            )

    else:
    
        if overall_status == "ELIGIBLE":

            message = (
                "Based on the information provided, "
                "at least one scheme satisfies the "
                "documented deterministic eligibility rules."
            )

        elif overall_status == "NEED_MORE_INFORMATION":

            message = (
                "Some schemes are relevant to your profile, "
                "but more information is required before "
                "eligibility can be confirmed."
            )

        elif overall_status == "NOT_ELIGIBLE":

            message = (
                "Based on the information provided, "
                "the relevant schemes contain eligibility "
                "conditions that are not satisfied."
            )

        elif overall_status == "RULES_REQUIRE_REVIEW":

            message = (
                "Relevant schemes were found, but their "
                "current eligibility cannot be safely "
                "confirmed from the available rules."
            )

        else:

            message = (
                "No sufficiently relevant scheme was found "
                "for the provided information."
            )

    # ========================================================
    # 13. Final structured response
    # ========================================================

    return {
        "query": query,

        "intent": intent,

        "detected_scheme": detected_scheme,

        "detected_state": detected_state,

        "topics": topics,

        "profile": compact_profile(
            profile
        ),

        "scope": scope,

        "retrieved_chunks": retrieved_chunks,

        "overall_status": overall_status,

        "next_questions": next_questions,

        "schemes_evaluated": len(
            evaluated_results
        ),

        "results": evaluated_results,

        # Used by app.py / LLM response generation.
        "response_language": response_language,

        "message": message,
    }


# ============================================================
# TERMINAL OUTPUT
# ============================================================

def print_eligibility_result(
    result: Dict[str, Any]
) -> None:

    print()
    print("=" * 80)
    print("ELIGIBILITY RESULT")
    print("=" * 80)

    print(
        "Intent:",
        result.get("intent")
    )

    print(
        "Response language:",
        result.get("response_language")
    )

    print(
        "Detected scheme:",
        result.get("detected_scheme")
    )

    print(
        "Detected state:",
        result.get("detected_state")
    )

    print(
        "Topics:",
        result.get("topics")
    )

    print(
        "Overall status:",
        result.get("overall_status")
    )

    print(
        "Profile:",
        result.get("profile")
    )

    print(
        "Retrieved chunks:",
        result.get("retrieved_chunks")
    )

    print(
        "Schemes evaluated:",
        result.get("schemes_evaluated")
    )

    print()

    for index, scheme in enumerate(
        result.get("results", []),
        start=1,
    ):

        print(
            f"{index:02d}. "
            f"{scheme.get('scheme_name')} "
            f"-> "
            f"{scheme.get('status')}"
        )

        print(
            "    Category:",
            scheme.get("category")
        )

        print(
            "    State:",
            scheme.get("state")
        )

        print(
            "    Relevance:",
            scheme.get(
                "eligibility_relevance"
            )
        )

        if scheme.get("missing_fields"):

            print(
                "    Missing fields:",
                ", ".join(
                    scheme.get(
                        "missing_fields",
                        [],
                    )
                ),
            )

        if scheme.get("failed_rules"):

            print(
                "    Failed rules:",
                len(
                    scheme.get(
                        "failed_rules",
                        [],
                    )
                ),
            )

        if scheme.get("unsupported_rules"):

            print(
                "    Unsupported rules:",
                len(
                    scheme.get(
                        "unsupported_rules",
                        [],
                    )
                ),
            )

        if scheme.get("questions"):

            print("    Questions:")

            for question in scheme.get(
                "questions",
                [],
            ):

                print(
                    "      -",
                    question.get("question"),
                )

        print()

    if result.get("next_questions"):

        print("=" * 80)
        print("NEXT QUESTIONS")
        print("=" * 80)

        for index, question in enumerate(
            result.get(
                "next_questions",
                [],
            ),
            start=1,
        ):

            print(
                f"{index}. "
                f"{question.get('question')}"
            )

    print("=" * 80)


# ============================================================
# TEST CASES
# ============================================================

if __name__ == "__main__":

    test_queries = [

        # English scholarship
        (
            "I am a student from Telangana. "
            "I got 85% in 12th and my family income "
            "is 3 lakhs. "
            "I am studying a regular degree course. "
            "Can I get a scholarship?"
        ),

        # Telugu scholarship
        (
            "నేను తెలంగాణకు చెందిన విద్యార్థిని. "
            "నాకు 12వ తరగతిలో 85% మార్కులు వచ్చాయి. "
            "మా కుటుంబ వార్షిక ఆదాయం 3 లక్షలు. "
            "నేను రెగ్యులర్ డిగ్రీ కోర్సు చదువుతున్నాను. "
            "నాకు స్కాలర్‌షిప్ వస్తుందా?"
        ),

        # Mixed Telugu + English
        (
            "నేను Telangana student ని. "
            "నాకు scholarship వస్తుందా?"
        ),

        # Agriculture
        (
            "I am a farmer from Telangana. "
            "What government schemes can I get?"
        ),

        # Housing
        (
            "I live in Telangana and I need help "
            "for building a house. "
            "Can I get a housing scheme?"
        ),

        # Health
        (
            "I am from Andhra Pradesh. "
            "Can I get government health insurance "
            "for hospital treatment?"
        ),

        # Pension
        (
            "I am a senior citizen from Telangana. "
            "Can I get a pension?"
        ),

        # Women
        (
            "I am a woman from Andhra Pradesh. "
            "What government benefits are available?"
        ),

        # Employment
        (
            "I am unemployed and looking for "
            "government employment assistance."
        ),

        # Business
        (
            "I want to start a small business. "
            "Can I get a government loan?"
        ),

        # Explicit scheme
        (
            "Am I eligible for PM KISAN?"
        ),
    ]

    for query in test_queries:

        result = check_eligibility(
            query,
            max_schemes=5,
        )

        print_eligibility_result(
            result
        )