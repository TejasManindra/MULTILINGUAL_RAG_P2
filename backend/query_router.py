from typing import Any, Dict, Optional
import re


# ============================================================
# STATE ALIASES
# ============================================================

STATE_ALIASES = {
    "telangana": "telangana",
    "telangana state": "telangana",
    "tg": "telangana",
    "ts": "telangana",

    "andhra pradesh": "andhra pradesh",
    "andhra": "andhra pradesh",
    "ap": "andhra pradesh",
}


# ============================================================
# SCHEME ALIASES
# ============================================================

SCHEME_ALIASES = {
    "pm kisan": "PM-KISAN",
    "pm-kisan": "PM-KISAN",
    "pmkisan": "PM-KISAN",

    "kisan credit card": "Kisan Credit Card",
    "kcc": "Kisan Credit Card",

    "ntr bharosa": "NTR Bharosa Pension Scheme",
    "thalliki vandanam": "Thalliki Vandanam",
    "deepam 2": "AP Deepam 2.0",
    "deepam": "AP Deepam 2.0",
    "stree shakti": "Stree Shakti",
    "annadata": "Annadata Sukhibhava – PM-KISAN",

    "rythu bharosa": "Rythu Bharosa",
    "gruhajyothi": "Gruha Jyothi",
    "gruha jyothi": "Gruha Jyothi",
    "maha lakshmi": "Maha Lakshmi",
    "kalyana lakshmi": "Kalyana Lakshmi",
    "shaadi mubarak": "Shaadi Mubarak",
    "cheyutha": "Cheyutha",
    "aarogyasri": "Rajiv Aarogyasri",

    "pmay": "Pradhan Mantri Awas Yojana",
    "pmay urban": "Pradhan Mantri Awas Yojana - Urban 2.0",
    "pmay-u": "Pradhan Mantri Awas Yojana - Urban 2.0",

    "central sector scholarship": "Central Sector Scholarship Scheme",
    "csss": "Central Sector Scholarship Scheme",

    "epass": "Telangana ePASS Scholarships",
    "epass scholarship": "Telangana ePASS Scholarships",
}


# ============================================================
# KEYWORDS
# ============================================================

ELIGIBILITY_PHRASES = [
    # English
    "am i eligible",
    "am i eligible for",
    "can i get",
    "can i get this",
    "can i get the",
    "can i get a",
    "do i qualify",
    "do i qualify for",
    "would i qualify",
    "will i qualify",
    "eligible for",
    "eligibility",
    "eligibility for",
    "qualify for",
    "qualified for",
    "can i apply",
    "can i apply for",
    "can i receive",
    "can i avail",
    "can i benefit",
    "do i get",
    "do i qualify",
    "which schemes can i get",
    "what schemes can i get",
    "what schemes am i eligible for",
    "which schemes am i eligible for",

    # Telugu
    "అర్హత",
    "అర్హుడిని",
    "అర్హురాలిని",
    "అర్హత ఉందా",
    "నాకు వస్తుందా",
    "నేను పొందగలనా",
    "నాకు అర్హత ఉందా",
]


DISCOVERY_PHRASES = [
    "what schemes",
    "which schemes",
    "schemes available",
    "government schemes",
    "schemes for me",
    "what benefits",
    "benefits available",
    "what can i get",
    "schemes do i have",
    "schemes are available",
]


APPLICATION_PHRASES = [
    "how to apply",
    "how can i apply",
    "where can i apply",
    "application process",
    "apply online",
    "application form",
    "documents required",
    "documents needed",
    "how do i apply",
]


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = str(text).lower().strip()

    # Normalize repeated whitespace.
    text = re.sub(r"\s+", " ", text)

    return text


# ============================================================
# STATE DETECTION
# ============================================================

def detect_state(query: str) -> Optional[str]:

    text = normalize_text(query)

    # Longest aliases first.
    for alias in sorted(
        STATE_ALIASES.keys(),
        key=len,
        reverse=True,
    ):
        if alias in text:
            return STATE_ALIASES[alias]

    return None


# ============================================================
# SCHEME DETECTION
# ============================================================

def detect_scheme(query: str) -> Optional[str]:

    text = normalize_text(query)

    for alias in sorted(
        SCHEME_ALIASES.keys(),
        key=len,
        reverse=True,
    ):
        if alias in text:
            return SCHEME_ALIASES[alias]

    return None


# ============================================================
# PROFILE DETECTION
# ============================================================

def detect_basic_profile(
    query: str,
) -> Dict[str, Any]:

    text = normalize_text(query)

    profile = {}

    # --------------------------------------------------------
    # Student
    # --------------------------------------------------------

    student_terms = [
        "student",
        "school student",
        "college student",
        "university student",
        "undergraduate",
        "postgraduate",
        "studying",
        "student from",
        "విద్యార్థి",
        "విద్యార్థిని",
    ]

    if any(term in text for term in student_terms):
        profile["occupation"] = "student"

    # --------------------------------------------------------
    # Farmer
    # --------------------------------------------------------

    farmer_terms = [
        "farmer",
        "farmers",
        "cultivator",
        "tenant farmer",
        "agricultural labour",
        "agricultural worker",
        "రైతు",
        "రైతును",
    ]

    if any(term in text for term in farmer_terms):
        profile["occupation"] = "farmer"

    # --------------------------------------------------------
    # Woman
    # --------------------------------------------------------

    if any(
        term in text
        for term in [
            "woman",
            "women",
            "female",
            "girl",
            "lady",
            "మహిళ",
            "స్త్రీ",
        ]
    ):
        profile["gender"] = "female"

    # --------------------------------------------------------
    # Senior citizen
    # --------------------------------------------------------

    if any(
        term in text
        for term in [
            "senior citizen",
            "elderly",
            "old age",
            "వృద్ధ",
        ]
    ):
        profile["occupation"] = "senior_citizen"

    # --------------------------------------------------------
    # Unemployed
    # --------------------------------------------------------

    if any(
        term in text
        for term in [
            "unemployed",
            "jobless",
            "without a job",
            "job seeker",
            "unemployment",
            "నిరుద్యోగి",
        ]
    ):
        profile["employment_status"] = "unemployed"

    return profile


# ============================================================
# INTENT DETECTION
# ============================================================

def _contains_phrase(
    text: str,
    phrases,
) -> bool:

    return any(
        phrase in text
        for phrase in phrases
    )


def detect_intent(
    query: str,
    detected_scheme: Optional[str] = None,
) -> str:

    text = normalize_text(query)

    # --------------------------------------------------------
    # IMPORTANT:
    # Eligibility must be checked BEFORE generic
    # scheme-information detection.
    # --------------------------------------------------------

    if _contains_phrase(
        text,
        ELIGIBILITY_PHRASES,
    ):
        return "ELIGIBILITY"

    # --------------------------------------------------------
    # Application
    # --------------------------------------------------------

    if _contains_phrase(
        text,
        APPLICATION_PHRASES,
    ):
        return "APPLICATION"

    # --------------------------------------------------------
    # Discovery
    # --------------------------------------------------------

    if _contains_phrase(
        text,
        DISCOVERY_PHRASES,
    ):
        return "SCHEME_DISCOVERY"

    # --------------------------------------------------------
    # Specific scheme without an explicit action
    # --------------------------------------------------------

    if detected_scheme:
        return "SCHEME_SPECIFIC"

    # --------------------------------------------------------
    # Default
    # --------------------------------------------------------

    return "SCHEME_INFO"


# ============================================================
# SEARCH SCOPE
# ============================================================

def build_search_scope(
    state: Optional[str],
) -> Dict[str, Any]:

    # Central schemes are always included.

    if state:

        return {
            "include_central": True,
            "include_state": True,
            "state": state,
        }

    return {
        "include_central": True,
        "include_state": False,
        "state": None,
    }


# ============================================================
# MAIN ROUTER
# ============================================================

def route_query(
    query: str,
) -> Dict[str, Any]:

    normalized_query = normalize_text(
        query
    )

    state = detect_state(
        normalized_query
    )

    scheme = detect_scheme(
        normalized_query
    )

    intent = detect_intent(
        normalized_query,
        scheme,
    )

    profile = detect_basic_profile(
        normalized_query
    )

    return {
        "query": query,

        "intent": intent,

        "detected_scheme": scheme,

        "detected_state": state,

        "profile": profile,

        "search_scope": build_search_scope(
            state
        ),
    }


# ============================================================
# TESTS
# ============================================================

if __name__ == "__main__":

    test_queries = [

        (
            "I am a student from Telangana. "
            "I got 85% in 12th and my family income "
            "is 3 lakhs. Can I get a scholarship?"
        ),

        (
            "I am a farmer from Telangana. "
            "What all schemes can I get?"
        ),

        (
            "How can I apply for Kalyana Lakshmi?"
        ),

        (
            "Tell me about PM-KISAN."
        ),

        (
            "I am a woman from Andhra Pradesh. "
            "Am I eligible for any schemes?"
        ),
    ]

    for query in test_queries:

        print()
        print("=" * 80)
        print(query)
        print("=" * 80)

        print(
            route_query(query)
        )