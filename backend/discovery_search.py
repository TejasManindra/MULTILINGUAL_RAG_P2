from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from backend.query_router import route_query
from backend.scheme_search import hybrid_search


DEFAULT_TOP_K = 60
FINAL_SCHEME_COUNT = 15


# ============================================================
# Topic keywords
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
        "degree",
        "school",
        "class",
        "12th",
        "10th",
        "pms",
        "epass",
        "vidya",
        "fee reimbursement",
        "tuition",
        "fellowship",
        "విద్యార్థి",
        "విద్యార్థులు",
        "స్కాలర్‌షిప్",
        "స్కాలర్షిప్",
        "విద్య",
        "కాలేజీ",
        "డిగ్రీ",
    ],

    "agriculture": [
        "farmer",
        "farmers",
        "farming",
        "agriculture",
        "agricultural",
        "crop",
        "cultivation",
        "cultivator",
        "tenant farmer",
        "landless farmer",
        "kisan",
        "rythu",
        "రైతు",
        "రైతులు",
        "వ్యవసాయం",
        "పంట",
    ],

    "housing": [
        "house",
        "housing",
        "home",
        "construction",
        "build a house",
        "own house",
        "roof",
        "awas",
        "indlu",
        "ఇల్లు",
        "ఇండ్లు",
        "గృహ",
        "హౌసింగ్",
    ],

    "health": [
        "health",
        "hospital",
        "medical",
        "medicine",
        "treatment",
        "surgery",
        "insurance",
        "aarogyasri",
        "pm-jay",
        "health card",
        "ఆరోగ్యం",
        "ఆసుపత్రి",
        "చికిత్స",
    ],

    "women": [
        "woman",
        "women",
        "girl",
        "girls",
        "mother",
        "widow",
        "women empowerment",
        "mahila",
        "మహిళ",
        "మహిళలు",
        "బాలిక",
    ],

    "pension": [
        "pension",
        "senior citizen",
        "elderly",
        "old age",
        "widow pension",
        "disability pension",
        "aasara",
        "bharosa pension",
        "పెన్షన్",
        "వృద్ధాప్య",
    ],

    "employment": [
        "job",
        "employment",
        "unemployed",
        "unemployment",
        "business",
        "self employment",
        "loan",
        "entrepreneur",
        "skill",
        "training",
        "vishwakarma",
        "mudra",
        "నిరుద్యోగ",
        "ఉద్యోగం",
        "వ్యాపారం",
    ],

    "food": [
        "food",
        "ration",
        "rice",
        "meal",
        "midday meal",
        "nutrition",
        "lpg",
        "cooking gas",
        "అన్నం",
        "రేషన్",
        "ఆహారం",
    ],
}


# ============================================================
# Scope
# ============================================================

def is_in_scope(
    scheme: Dict[str, Any],
    detected_state: Optional[str],
) -> bool:

    government_level = str(
        scheme.get("government_level") or ""
    ).lower()

    state = str(
        scheme.get("state") or ""
    ).lower()

    # Central schemes are always in scope.
    if government_level == "central":
        return True

    # If the user specified a state, only that state
    # should be included.
    if detected_state:
        return state == detected_state.lower()

    # No state supplied:
    # keep only Central schemes.
    return False


# ============================================================
# Topic detection
# ============================================================

def detect_topics(query: str) -> List[str]:
    """
    Detect broad user topics.

    This is deliberately keyword-based.
    It does not make eligibility decisions.
    """

    text = query.lower()

    scores: Dict[str, int] = {}

    for topic, keywords in TOPIC_KEYWORDS.items():

        score = 0

        for keyword in keywords:

            if keyword.lower() in text:
                score += 1

        if score > 0:
            scores[topic] = score

    # Highest scoring topics first.
    return [
        topic
        for topic, _ in sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    ]


# ============================================================
# Scheme topic inference
# ============================================================

def infer_scheme_topics(
    scheme: Dict[str, Any],
) -> List[str]:

    text_parts = [
        scheme.get("scheme_name"),
        scheme.get("category"),
        scheme.get("subcategory"),
        scheme.get("target_beneficiary"),
        scheme.get("benefit_description"),
        scheme.get("eligibility_rules"),
    ]

    text = " ".join(
        str(x)
        for x in text_parts
        if x is not None
    ).lower()

    topics = []

    for topic, keywords in TOPIC_KEYWORDS.items():

        if any(
            keyword.lower() in text
            for keyword in keywords
        ):
            topics.append(topic)

    return topics


# ============================================================
# Topic score
# ============================================================

def calculate_topic_score(
    scheme: Dict[str, Any],
    query_topics: List[str],
) -> float:

    if not query_topics:
        return 0.0

    scheme_topics = infer_scheme_topics(
        scheme
    )

    if not scheme_topics:
        return 0.0

    overlap = len(
        set(query_topics)
        & set(scheme_topics)
    )

    if overlap == 0:
        return 0.0

    # Strong but controlled bonus.
    return min(
        0.25,
        0.10 * overlap,
    )


# ============================================================
# Preserve structured scheme metadata
# ============================================================

def _first_non_empty(
    current: Any,
    candidate: Any,
) -> Any:

    if current is not None:
        if current != "":
            if current != []:
                if current != {}:
                    return current

    return candidate


def _merge_rule_lists(
    current: Any,
    candidate: Any,
) -> Any:
    """
    Preserve structured eligibility rules.

    This is the important fix.

    Discovery previously discarded eligibility_rules
    during scheme aggregation.
    """

    values = []

    for item in (current, candidate):

        if not item:
            continue

        if isinstance(item, list):

            for rule in item:

                if rule not in values:
                    values.append(rule)

    return values if values else None


# ============================================================
# Scheme deduplication
# ============================================================

def deduplicate_schemes(
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    grouped: Dict[str, Dict[str, Any]] = {}

    for chunk in chunks:

        scheme_id = (
            chunk.get("scheme_id")
            or chunk.get("scheme_name")
            or chunk.get("id")
        )

        if not scheme_id:
            continue

        if scheme_id not in grouped:

            grouped[scheme_id] = {
                "scheme_id": scheme_id,

                "scheme_name": chunk.get(
                    "scheme_name"
                ),

                "government_level": chunk.get(
                    "government_level"
                ),

                "state": chunk.get(
                    "state"
                ),

                "ministry_department": chunk.get(
                    "ministry_department"
                ),

                "category": chunk.get(
                    "category"
                ),

                "subcategory": chunk.get(
                    "subcategory"
                ),

                "target_beneficiary": chunk.get(
                    "target_beneficiary"
                ),

                "scheme_status": chunk.get(
                    "scheme_status"
                ),

                "benefit_description": chunk.get(
                    "benefit_description"
                ),

                # IMPORTANT:
                # preserve structured rules.
                "eligibility_rules": chunk.get(
                    "eligibility_rules"
                ),

                "exclusion_rules": chunk.get(
                    "exclusion_rules"
                ),

                "verification_status": chunk.get(
                    "verification_status"
                ),

                "source_url": chunk.get(
                    "source_url"
                ),

                "source_status": chunk.get(
                    "source_status"
                ),

                "source_file": chunk.get(
                    "source_file"
                ),

                "document_title": chunk.get(
                    "document_title"
                ),

                "vector_score": chunk.get(
                    "vector_score",
                    0.0,
                ),

                "exact_score": chunk.get(
                    "exact_score",
                    0.0,
                ),

                "state_score": chunk.get(
                    "state_score",
                    0.0,
                ),

                "final_score": chunk.get(
                    "final_score",
                    0.0,
                ),

                "chunks": [],
            }

        else:

            existing = grouped[scheme_id]

            # ------------------------------------------------
            # Preserve metadata from any chunk that contains it
            # ------------------------------------------------

            fields = [
                "scheme_name",
                "government_level",
                "state",
                "ministry_department",
                "category",
                "subcategory",
                "target_beneficiary",
                "scheme_status",
                "benefit_description",
                "exclusion_rules",
                "verification_status",
                "source_url",
                "source_status",
                "source_file",
                "document_title",
            ]

            for field in fields:

                existing[field] = _first_non_empty(
                    existing.get(field),
                    chunk.get(field),
                )

            # ------------------------------------------------
            # IMPORTANT FIX:
            # merge structured eligibility rules
            # ------------------------------------------------

            existing["eligibility_rules"] = (
                _merge_rule_lists(
                    existing.get("eligibility_rules"),
                    chunk.get("eligibility_rules"),
                )
            )

            # ------------------------------------------------
            # Keep strongest retrieval scores
            # ------------------------------------------------

            existing["vector_score"] = max(
                existing.get("vector_score") or 0.0,
                chunk.get("vector_score") or 0.0,
            )

            existing["exact_score"] = max(
                existing.get("exact_score") or 0.0,
                chunk.get("exact_score") or 0.0,
            )

            existing["state_score"] = max(
                existing.get("state_score") or 0.0,
                chunk.get("state_score") or 0.0,
            )

            existing["final_score"] = max(
                existing.get("final_score") or 0.0,
                chunk.get("final_score") or 0.0,
            )

        # ----------------------------------------------------
        # Preserve chunk
        # ----------------------------------------------------

        grouped[scheme_id]["chunks"].append(
            chunk
        )

    return list(
        grouped.values()
    )


# ============================================================
# Add topic score
# ============================================================

def apply_topic_ranking(
    schemes: List[Dict[str, Any]],
    query_topics: List[str],
) -> List[Dict[str, Any]]:

    for scheme in schemes:

        topic_score = calculate_topic_score(
            scheme,
            query_topics,
        )

        scheme["topic_score"] = topic_score

        base_score = (
            scheme.get("final_score")
            or 0.0
        )

        scheme["rank_score"] = (
            base_score
            + topic_score
        )

    schemes.sort(
        key=lambda x: (
            x.get("rank_score") or 0.0
        ),
        reverse=True,
    )

    return schemes


# ============================================================
# Main discovery function
# ============================================================

def discover_schemes(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    final_count: int = FINAL_SCHEME_COUNT,
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # Route query
    # --------------------------------------------------------

    routed = route_query(
        query
    )

    intent = routed.get(
        "intent"
    )

    detected_state = routed.get(
        "detected_state"
    )

    # --------------------------------------------------------
    # Detect broad topic
    # --------------------------------------------------------

    query_topics = detect_topics(
        query
    )

    # --------------------------------------------------------
    # Hybrid retrieval
    # --------------------------------------------------------

    search_output = hybrid_search(
        query,
        top_k=top_k,
    )

    # Existing hybrid_search can return:
    #
    # (detected_scheme, detected_state, results)
    #
    # or results directly.

    detected_scheme_from_search = None

    if (
        isinstance(search_output, tuple)
        and len(search_output) == 3
    ):

        (
            detected_scheme_from_search,
            detected_state_from_search,
            retrieved_chunks,
        ) = search_output

        if not detected_state:
            detected_state = (
                detected_state_from_search
            )

    else:

        retrieved_chunks = search_output

    if retrieved_chunks is None:
        retrieved_chunks = []

    # --------------------------------------------------------
    # Geographic filtering
    # --------------------------------------------------------

    scoped_chunks = [
        chunk
        for chunk in retrieved_chunks
        if is_in_scope(
            chunk,
            detected_state,
        )
    ]

    # --------------------------------------------------------
    # Scheme aggregation
    # --------------------------------------------------------

    schemes = deduplicate_schemes(
        scoped_chunks
    )

    # --------------------------------------------------------
    # Topic-aware ranking
    # --------------------------------------------------------

    schemes = apply_topic_ranking(
        schemes,
        query_topics,
    )

    # --------------------------------------------------------
    # Limit final schemes
    # --------------------------------------------------------

    schemes = schemes[
        :final_count
    ]

    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return {
        "query": query,

        "intent": intent,

        "detected_scheme": (
            detected_scheme_from_search
            or routed.get("detected_scheme")
        ),

        "detected_state": detected_state,

        "profile": routed.get(
            "profile",
            {},
        ),

        "scope": routed.get(
            "search_scope",
            {},
        ),

        "topics": query_topics,

        "retrieved_chunks": len(
            scoped_chunks
        ),

        "schemes": schemes,
    }


# ============================================================
# Test
# ============================================================

if __name__ == "__main__":

    query = (
        "I am a student from Telangana. "
        "I got 85% in 12th and my family income "
        "is 3 lakhs. "
        "I am studying a regular degree course. "
        "Can I get a scholarship?"
    )

    result = discover_schemes(
        query,
        top_k=60,
        final_count=10,
    )

    print()
    print("=" * 80)
    print("DISCOVERY TEST")
    print("=" * 80)

    print(
        "Intent:",
        result["intent"],
    )

    print(
        "State:",
        result["detected_state"],
    )

    print(
        "Topics:",
        result["topics"],
    )

    print(
        "Retrieved chunks:",
        result["retrieved_chunks"],
    )

    print()

    for index, scheme in enumerate(
        result["schemes"],
        start=1,
    ):

        print(
            f"{index:02d}. "
            f"{scheme.get('scheme_name')}"
        )

        print(
            "    ID:",
            scheme.get("scheme_id"),
        )

        print(
            "    Base:",
            round(
                scheme.get("final_score") or 0,
                4,
            ),
        )

        print(
            "    Topic:",
            round(
                scheme.get("topic_score") or 0,
                4,
            ),
        )

        print(
            "    Rank:",
            round(
                scheme.get("rank_score") or 0,
                4,
            ),
        )

        print(
            "    Rules:",
            "PRESENT"
            if scheme.get("eligibility_rules")
            else "MISSING",
        )

        print()