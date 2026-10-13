from __future__ import annotations

from typing import Any, Dict, List, Optional
import re

from backend.profile_mapper import (
    extract_profile,
    compact_profile,
)

from backend.discovery_search import (
    discover_schemes,
)

from backend.rule_evaluator import (
    evaluate_scheme_rules,
)

from backend.question_generator import (
    generate_questions,
)


# ============================================================
# CONFIG
# ============================================================

DEFAULT_RETRIEVAL_TOP_K = 60
DEFAULT_MAX_SCHEMES = 10
MAX_NEXT_QUESTIONS = 5
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
# TOPICS
# ============================================================

TOPIC_KEYWORDS = {

    "agriculture": [
        "farmer",
        "farmers",
        "farmer",
        "farming",
        "agriculture",
        "agricultural",
        "cultivation",
        "cultivator",
        "crop",
        "crops",
        "land",
        "farmland",
        "tenant farmer",
        "tenant",
        "sharecropper",
        "kisan",
        "rythu",

        "రైతు",
        "రైతులు",
        "వ్యవసాయం",
        "వ్యవసాయ",
        "పంట",
        "పంటలు",
        "సాగు",
        "కౌలు రైతు",
        "కిసాన్",
    ],

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

        "స్కాలర్‌షిప్",
        "స్కాలర్షిప్",
        "విద్యార్థి",
        "విద్యార్థులు",
        "విద్య",
        "చదువు",
        "కాలేజీ",
        "కళాశాల",
        "యూనివర్సిటీ",
        "ఫీజు",
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

        "ఇల్లు",
        "ఇంటి",
        "గృహ",
        "గృహం",
        "గృహ నిర్మాణం",
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

        "ఆరోగ్యం",
        "వైద్యం",
        "ఆసుపత్రి",
        "చికిత్స",
        "ఆరోగ్యశ్రీ",
    ],

    "pension": [
        "pension",
        "senior citizen",
        "old age",
        "widow",
        "disability pension",
        "social security",

        "పెన్షన్",
        "పింఛన్",
        "వృద్ధాప్య",
        "వృద్ధులు",
        "వితంతువు",
        "దివ్యాంగ",
    ],

    "women": [
        "woman",
        "women",
        "girl",
        "girls",
        "female",
        "mother",
        "women empowerment",
        "marriage assistance",

        "మహిళ",
        "మహిళలు",
        "స్త్రీ",
        "బాలిక",
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

        "ఉద్యోగం",
        "నిరుద్యోగి",
        "నిరుద్యోగం",
        "ఉపాధి",
        "కార్మికుడు",
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

        "వ్యాపారం",
        "వ్యాపారి",
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
        "food security",

        "ఆహారం",
        "రేషన్",
        "బియ్యం",
        "ధాన్యం",
        "పోషణ",
    ],

    "disability": [
        "disabled",
        "disability",
        "divyang",
        "pwd",
        "differently abled",

        "దివ్యాంగ",
        "వికలాంగ",
        "వైకల్యం",
    ],
}


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(
    value: Any,
) -> str:

    if value is None:
        return ""

    text = str(value).lower().strip()

    return re.sub(
        r"\s+",
        " ",
        text,
    )


# ============================================================
# RESPONSE LANGUAGE
# ============================================================

def detect_response_language(
    query: str,
) -> str:

    query = query or ""

    telugu_chars = sum(
        1
        for ch in query
        if "\u0C00" <= ch <= "\u0C7F"
    )

    english_chars = sum(
        1
        for ch in query
        if ch.isascii()
        and ch.isalpha()
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

    topics = []

    if discovery:

        discovered_topics = (
            discovery.get("topics", [])
            or []
        )

        for topic in discovered_topics:

            topic = _normalize(topic)

            if (
                topic
                and topic not in topics
            ):
                topics.append(topic)

    normalized_query = _normalize(
        query
    )

    for topic, keywords in TOPIC_KEYWORDS.items():

        for keyword in keywords:

            keyword = _normalize(
                keyword
            )

            if (
                keyword
                and keyword in normalized_query
            ):
                if topic not in topics:
                    topics.append(topic)

                break

    return topics


# ============================================================
# SCHEME TEXT
# ============================================================

def _scheme_search_text(
    scheme: Dict[str, Any],
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

    parts = []

    for field in fields:

        if field is None:
            continue

        if isinstance(field, list):

            for item in field:
                parts.append(
                    _normalize(item)
                )

        elif isinstance(field, dict):

            parts.append(
                _normalize(field)
            )

        else:

            parts.append(
                _normalize(field)
            )

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

    category = _normalize(
        scheme.get("category")
    )

    subcategory = _normalize(
        scheme.get("subcategory")
    )

    target = _normalize(
        scheme.get("target_beneficiary")
    )

    scheme_name = _normalize(
        scheme.get("scheme_name")
    )

    benefit = _normalize(
        scheme.get("benefit_description")
    )

    eligibility = _normalize(
        scheme.get("eligibility_rules")
    )

    full_text = " ".join([
        category,
        subcategory,
        target,
        scheme_name,
        benefit,
        eligibility,
    ])

    topic_scores = []

    strong_terms = {

        "agriculture": [
            "agriculture",
            "agricultural",
            "farmer",
            "farmers",
            "farming",
            "cultivation",
            "cultivator",
            "crop",
            "crops",
            "kisan",
            "rythu",
            "tenant farmer",
            "sharecropper",
            "agricultural credit",
            "crop insurance",
        ],

        "scholarship": [
            "scholarship",
            "student",
            "students",
            "education",
            "college",
            "university",
            "school",
            "fee reimbursement",
        ],

        "housing": [
            "housing",
            "house",
            "home",
            "shelter",
            "pucca house",
        ],

        "health": [
            "health",
            "medical",
            "hospital",
            "treatment",
            "aarogyasri",
        ],

        "pension": [
            "pension",
            "old age",
            "widow",
            "social security",
        ],

        "women": [
            "women",
            "woman",
            "girl",
            "female",
            "mother",
        ],

        "employment": [
            "employment",
            "job",
            "worker",
            "skill",
            "training",
            "livelihood",
        ],

        "business": [
            "business",
            "entrepreneur",
            "enterprise",
            "startup",
            "mudra",
            "credit",
            "loan",
        ],

        "food": [
            "food",
            "ration",
            "rice",
            "nutrition",
        ],

        "disability": [
            "disability",
            "disabled",
            "divyang",
            "pwd",
        ],
    }

    for topic in topics:

        terms = strong_terms.get(
            topic,
            TOPIC_KEYWORDS.get(
                topic,
                [],
            ),
        )

        matches = 0

        for term in terms:

            if _normalize(term) in full_text:
                matches += 1

        if matches == 0:
            topic_scores.append(0.0)

        elif category:
            category_match = any(
                _normalize(term)
                in category
                for term in terms
            )

            if category_match:
                topic_scores.append(1.0)
            else:
                topic_scores.append(0.70)

        else:
            topic_scores.append(0.50)

    return round(
        max(topic_scores)
        if topic_scores
        else 0.0,
        6,
    )


# ============================================================
# TOPIC GUARD
# ============================================================

def _passes_topic_guard(
    scheme: Dict[str, Any],
    topics: List[str],
    profile: Dict[str, Any],
) -> bool:

    if not topics:
        return True

    category = _normalize(
        scheme.get("category")
    )

    subcategory = _normalize(
        scheme.get("subcategory")
    )

    target = _normalize(
        scheme.get("target_beneficiary")
    )

    scheme_name = _normalize(
        scheme.get("scheme_name")
    )

    combined = " ".join([
        category,
        subcategory,
        target,
        scheme_name,
    ])

    # --------------------------------------------------------
    # Agriculture
    # --------------------------------------------------------

    if "agriculture" in topics:

        agriculture_terms = [
            "agriculture",
            "agricultural",
            "farmer",
            "farmers",
            "farming",
            "cultivation",
            "cultivator",
            "crop",
            "crops",
            "kisan",
            "rythu",
            "tenant farmer",
            "sharecropper",
            "agricultural credit",
            "crop insurance",
            "farm mechanization",
        ]

        if not any(
            _normalize(term) in combined
            for term in agriculture_terms
        ):
            return False

    # --------------------------------------------------------
    # Scholarship
    # --------------------------------------------------------

    if "scholarship" in topics:

        terms = [
            "scholarship",
            "student",
            "students",
            "education",
            "college",
            "university",
            "school",
            "fee reimbursement",
        ]

        if not any(
            _normalize(term) in combined
            for term in terms
        ):
            return False

    # --------------------------------------------------------
    # Housing
    # --------------------------------------------------------

    if "housing" in topics:

        terms = [
            "housing",
            "house",
            "home",
            "shelter",
            "pucca house",
        ]

        if not any(
            _normalize(term) in combined
            for term in terms
        ):
            return False

    # --------------------------------------------------------
    # Health
    # --------------------------------------------------------

    if "health" in topics:

        terms = [
            "health",
            "medical",
            "hospital",
            "treatment",
            "aarogyasri",
        ]

        if not any(
            _normalize(term) in combined
            for term in terms
        ):
            return False

    # --------------------------------------------------------
    # Pension
    # --------------------------------------------------------

    if "pension" in topics:

        terms = [
            "pension",
            "old age",
            "widow",
            "social security",
        ]

        if not any(
            _normalize(term) in combined
            for term in terms
        ):
            return False

    return True


# ============================================================
# PROFILE RELEVANCE
# ============================================================

def _profile_relevance(
    scheme: Dict[str, Any],
    profile: Dict[str, Any],
) -> float:

    if not profile:
        return 0.0

    text = _scheme_search_text(
        scheme
    )

    score = 0.0

    # --------------------------------------------------------
    # Farmer
    # --------------------------------------------------------

    is_farmer = (
        profile.get("occupation")
        == "farmer"
        or profile.get("tenant_farmer")
        is True
        or profile.get("landholder")
        is True
    )

    if is_farmer:

        farmer_terms = [
            "farmer",
            "farmers",
            "agriculture",
            "agricultural",
            "cultivator",
            "kisan",
            "rythu",
            "crop",
        ]

        if any(
            _normalize(term) in text
            for term in farmer_terms
        ):
            score += 0.30

    # --------------------------------------------------------
    # Tenant farmer
    # --------------------------------------------------------

    if profile.get(
        "tenant_farmer"
    ) is True:

        tenant_terms = [
            "tenant farmer",
            "tenant farmers",
            "tenant cultivator",
            "sharecropper",
            "sharecroppers",
            "oral lessee",
            "lessee",
            "tenant",
            "cultivator",
        ]

        if any(
            _normalize(term) in text
            for term in tenant_terms
        ):
            score += 0.25

    # --------------------------------------------------------
    # Student
    # --------------------------------------------------------

    if profile.get(
        "student"
    ) is True:

        student_terms = [
            "student",
            "students",
            "education",
            "scholarship",
            "college",
            "university",
            "school",
        ]

        if any(
            _normalize(term) in text
            for term in student_terms
        ):
            score += 0.25

    # --------------------------------------------------------
    # Disability
    # --------------------------------------------------------

    if profile.get(
        "disability"
    ) is True:

        terms = [
            "disability",
            "disabled",
            "divyang",
            "pwd",
        ]

        if any(
            _normalize(term) in text
            for term in terms
        ):
            score += 0.25

    return min(
        round(score, 6),
        1.0,
    )


# ============================================================
# RELEVANCE
# ============================================================

def _calculate_relevance(
    scheme: Dict[str, Any],
    topics: List[str],
    profile: Dict[str, Any],
) -> float:

    retrieval_score = float(
        scheme.get(
            "final_score",
            0.0,
        )
        or 0.0
    )

    topic_score = _topic_score(
        scheme,
        topics,
    )

    profile_score = _profile_relevance(
        scheme,
        profile,
    )

    score = (
        retrieval_score * 0.45
        + topic_score * 0.35
        + profile_score * 0.20
    )

    return round(
        score,
        6,
    )


# ============================================================
# STATUS HELPERS
# ============================================================

def _status_text(
    scheme: Dict[str, Any],
) -> str:

    return _normalize(
        scheme.get(
            "scheme_status"
        )
    )


def _is_historical_or_proposed(
    scheme: Dict[str, Any],
) -> bool:

    status = _status_text(
        scheme
    )

    markers = [
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
        for marker in markers
    )


def _is_current_status_confirmed(
    scheme: Dict[str, Any],
) -> bool:

    status = _status_text(
        scheme
    )

    if not status:
        return True

    markers = [
        "active_current",
        "active",
        "current",
        "ongoing",
        "operational",
    ]

    return any(
        marker in status
        for marker in markers
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

        matches = []

        for scheme in schemes:

            if (
                scheme.get("scheme_id")
                == detected_scheme
            ):
                matches.append(
                    scheme
                )

        return matches[
            :max_schemes
        ]

    # --------------------------------------------------------
    # Normal discovery
    # --------------------------------------------------------

    candidates = []

    for scheme in schemes:

        topic_score = _topic_score(
            scheme,
            topics,
        )

        profile_score = _profile_relevance(
            scheme,
            profile,
        )

        relevance = _calculate_relevance(
            scheme,
            topics,
            profile,
        )

        # ----------------------------------------------------
        # Hard topic guard
        # ----------------------------------------------------

        if topics:

            if not _passes_topic_guard(
                scheme,
                topics,
                profile,
            ):
                continue

            if topic_score <= 0:
                continue

        if relevance < MIN_RELEVANCE_SCORE:
            continue

        item = dict(
            scheme
        )

        item["_topic_score"] = (
            topic_score
        )

        item["_beneficiary_score"] = (
            profile_score
        )

        item["_eligibility_relevance"] = (
            relevance
        )

        item["relevance_score"] = (
            relevance
        )

        candidates.append(
            item
        )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    candidates.sort(
        key=lambda item: (
            item.get(
                "_topic_score",
                0.0,
            ),
            item.get(
                "_beneficiary_score",
                0.0,
            ),
            item.get(
                "_eligibility_relevance",
                0.0,
            ),
            item.get(
                "final_score",
                0.0,
            ),
        ),
        reverse=True,
    )

    return candidates[
        :max_schemes
    ]


# ============================================================
# SCHEME RESULT
# ============================================================

def _scheme_result(
    scheme: Dict[str, Any],
    evaluation: Dict[str, Any],
    relevance: float,
) -> Dict[str, Any]:

    status = evaluation.get(
        "status",
        "RULES_REQUIRE_REVIEW",
    )

    result = dict(
        scheme
    )

    result["status"] = status

    result["evaluation"] = (
        evaluation
    )

    result["missing_fields"] = (
        evaluation.get(
            "missing_fields",
            [],
        )
        or []
    )

    result["failed_rules"] = (
        evaluation.get(
            "failed_rules",
            [],
        )
        or []
    )

    result["unsupported_rules"] = (
        evaluation.get(
            "unsupported_rules",
            [],
        )
        or []
    )

    result["relevance_score"] = (
        relevance
    )

    result["questions"] = (
        generate_questions(
            evaluation,
            max_questions=3,
        )
    )

    result[
        "current_status_confirmed"
    ] = _is_current_status_confirmed(
        scheme
    )

    result[
        "historical_or_proposed"
    ] = _is_historical_or_proposed(
        scheme
    )

    return result


# ============================================================
# SORT RESULTS
# ============================================================

def _sort_results(
    results: List[Dict[str, Any]],
):

    return sorted(
        results,
        key=lambda item: (
            STATUS_PRIORITY.get(
                item.get(
                    "status"
                ),
                99,
            ),
            -float(
                item.get(
                    "relevance_score",
                    0.0,
                )
                or 0.0
            ),
        ),
    )


# ============================================================
# NEXT QUESTIONS
# ============================================================

def _select_next_questions(
    results: List[Dict[str, Any]],
) -> List[str]:

    questions = []

    seen = set()

    for result in results:

        if result.get(
            "status"
        ) != "NEED_MORE_INFORMATION":
            continue

        for question in (
            result.get(
                "questions",
                [],
            )
            or []
        ):

            question = str(
                question
            ).strip()

            if not question:
                continue

            key = question.lower()

            if key in seen:
                continue

            seen.add(key)

            questions.append(
                question
            )

            if len(
                questions
            ) >= MAX_NEXT_QUESTIONS:
                return questions

    return questions


# ============================================================
# OVERALL STATUS
# ============================================================

def _calculate_overall_status(
    results: List[Dict[str, Any]],
) -> str:

    if not results:
        return "NO_RELEVANT_SCHEME"

    statuses = [
        result.get("status")
        for result in results
    ]

    if "ELIGIBLE" in statuses:
        return "ELIGIBLE"

    if "NEED_MORE_INFORMATION" in statuses:
        return "NEED_MORE_INFORMATION"

    if "NOT_ELIGIBLE" in statuses:
        return "NOT_ELIGIBLE"

    if "RULES_REQUIRE_REVIEW" in statuses:
        return "RULES_REQUIRE_REVIEW"

    if (
        "CURRENT_STATUS_UNCONFIRMED"
        in statuses
    ):
        return "CURRENT_STATUS_UNCONFIRMED"

    if (
        "HISTORICAL_OR_PROPOSED"
        in statuses
    ):
        return "HISTORICAL_OR_PROPOSED"

    return "NO_RELEVANT_SCHEME"


# ============================================================
# MAIN
# ============================================================

def check_eligibility(
    query: str,
    max_schemes: int = DEFAULT_MAX_SCHEMES,
) -> Dict[str, Any]:

    query = (
        query or ""
    ).strip()

    response_language = (
        detect_response_language(
            query
        )
    )

    # --------------------------------------------------------
    # Profile
    # --------------------------------------------------------

    profile = extract_profile(
        query
    )

    profile = compact_profile(
        profile
    )

    # --------------------------------------------------------
    # Safety:
    # percentage != percentile
    # --------------------------------------------------------

    normalized_query = query.lower()

    explicit_percentile = bool(
        re.search(
            r"\bpercentile\b",
            normalized_query,
            re.IGNORECASE,
        )
        or "పర్సెంటైల్"
        in query
    )

    explicit_percentage = bool(
        re.search(
            r"\b(?:percentage|percent|marks|%)\b",
            normalized_query,
            re.IGNORECASE,
        )
        or "%"
        in query
        or "మార్కులు"
        in query
    )

    if (
        explicit_percentage
        and not explicit_percentile
        and profile.get(
            "class_12_percentile"
        ) is not None
    ):
        profile[
            "class_12_percentile"
        ] = None

    # --------------------------------------------------------
    # Discovery
    # --------------------------------------------------------

    discovery = discover_schemes(
        query,
        top_k=DEFAULT_RETRIEVAL_TOP_K,
        final_count=max(
            max_schemes * 3,
            15,
        ),
    )

    if not discovery:
        discovery = {}

    # --------------------------------------------------------
    # Discovery metadata
    # --------------------------------------------------------

    topics = _detect_topics(
        query,
        discovery,
    )

    detected_scheme = (
        discovery.get(
            "detected_scheme"
        )
        or discovery.get(
            "scheme_id"
        )
    )

    detected_state = (
        discovery.get(
            "detected_state"
        )
        or profile.get(
            "state"
        )
    )

    # --------------------------------------------------------
    # Get scheme candidates
    # --------------------------------------------------------

    raw_schemes = (
        discovery.get(
            "schemes"
        )
        or discovery.get(
            "results"
        )
        or []
    )

    # Some versions of discovery_search may return
    # scheme records under another key.
    if not raw_schemes:

        raw_schemes = (
            discovery.get(
                "retrieved_schemes"
            )
            or []
        )

    candidates = (
        _select_candidate_schemes(
            schemes=raw_schemes,
            query=query,
            profile=profile,
            topics=topics,
            detected_scheme=detected_scheme,
            max_schemes=max_schemes,
        )
    )

    # --------------------------------------------------------
    # Evaluate
    # --------------------------------------------------------

    results = []

    for scheme in candidates:

        relevance = float(
            scheme.get(
                "relevance_score",
                scheme.get(
                    "_eligibility_relevance",
                    0.0,
                ),
            )
            or 0.0
        )

        # ----------------------------------------------------
        # Historical / proposed
        # ----------------------------------------------------

        if _is_historical_or_proposed(
            scheme
        ):

            evaluation = {
                "status":
                    "RULES_REQUIRE_REVIEW",

                "missing_fields":
                    [],

                "failed_rules":
                    [],

                "unsupported_rules":
                    [],

                "reason":
                    "The scheme is historical, proposed, "
                    "unconfirmed, discontinued, or otherwise "
                    "not established as a current scheme.",
            }

        # ----------------------------------------------------
        # Current status unknown
        # ----------------------------------------------------

        elif not _is_current_status_confirmed(
            scheme
        ):

            evaluation = {
                "status":
                    "CURRENT_STATUS_UNCONFIRMED",

                "missing_fields":
                    [],

                "failed_rules":
                    [],

                "unsupported_rules":
                    [],

                "reason":
                    "The current operational status of "
                    "this scheme could not be confirmed.",
            }

        # ----------------------------------------------------
        # Deterministic rule evaluation
        # ----------------------------------------------------

        else:

            evaluation = evaluate_scheme_rules(
                scheme=scheme,
                profile=profile,
            )

        result = _scheme_result(
            scheme,
            evaluation,
            relevance,
        )

        results.append(
            result
        )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    results = _sort_results(
        results
    )

    # --------------------------------------------------------
    # Questions
    # --------------------------------------------------------

    next_questions = (
        _select_next_questions(
            results
        )
    )

    # --------------------------------------------------------
    # Overall
    # --------------------------------------------------------

    overall_status = (
        _calculate_overall_status(
            results
        )
    )

    # --------------------------------------------------------
    # User message
    # --------------------------------------------------------

    if response_language == "telugu":

        if overall_status == "ELIGIBLE":

            message = (
                "మీరు అందించిన వివరాల ఆధారంగా "
                "కొన్ని పథకాల అర్హత ప్రమాణాలు "
                "నెరవేరినట్లు గుర్తించబడింది."
            )

        elif overall_status == "NEED_MORE_INFORMATION":

            message = (
                "మీ ప్రొఫైల్‌కు సరిపడే పథకాలు "
                "కనుగొనబడ్డాయి. తుది అర్హతను "
                "నిర్ధారించడానికి కొన్ని వివరాలు "
                "ఇంకా అవసరం."
            )

        elif overall_status == "NOT_ELIGIBLE":

            message = (
                "పరిశీలించిన పథకాలలో కొన్ని "
                "అర్హత ప్రమాణాలు నెరవేరలేదు."
            )

        else:

            message = (
                "సంబంధిత పథకాలు కనుగొనబడ్డాయి. "
                "మరింత పరిశీలన అవసరం."
            )

    else:

        if overall_status == "ELIGIBLE":

            message = (
                "Based on the information provided, "
                "one or more schemes have passed "
                "the documented eligibility checks."
            )

        elif overall_status == "NEED_MORE_INFORMATION":

            message = (
                "The following government schemes "
                "match your profile. Eligibility is "
                "still pending because some required "
                "information is missing."
            )

        elif overall_status == "NOT_ELIGIBLE":

            message = (
                "Based on the documented rules, "
                "some evaluated schemes currently "
                "have eligibility conditions that "
                "are not satisfied."
            )

        else:

            message = (
                "Relevant government schemes were "
                "found, but additional review is "
                "required."
            )

    return {

        "query":
            query,

        "intent":
            discovery.get(
                "intent"
            ),

        "detected_scheme":
            detected_scheme,

        "detected_state":
            detected_state,

        "topics":
            topics,

        "profile":
            profile,

        "scope":
            discovery.get(
                "search_scope",
                {},
            ),

        "retrieved_chunks":
            discovery.get(
                "retrieved_chunks",
                [],
            ),

        "overall_status":
            overall_status,

        "next_questions":
            next_questions,

        "schemes_evaluated":
            len(results),

        "results":
            results,

        "response_language":
            response_language,

        "message":
            message,
    }