"""
Eligibility rule normalization.

Converts common eligibility patterns from scheme text
into structured rules for the deterministic eligibility engine.

Important:
- This parser is conservative.
- It only creates a structured rule when a pattern is reasonably clear.
- Original eligibility text remains the source of truth.
"""

from __future__ import annotations

import re
from typing import Any, Dict


def _clean(text: Any) -> str:
    if text is None:
        return ""

    return str(text).strip()


def _contains(text: str, patterns) -> bool:
    text_lower = text.lower()

    return any(
        re.search(pattern, text_lower)
        for pattern in patterns
    )


def _extract_number(pattern: str, text: str):
    match = re.search(pattern, text.lower())

    if not match:
        return None

    try:
        return float(match.group(1))
    except (ValueError, TypeError):
        return None


def normalize_eligibility_rules(
    scheme: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert scheme eligibility/exclusion text
    into conservative structured rules.
    """

    eligibility = _clean(
        scheme.get("eligibility_rules")
    )

    exclusions = _clean(
        scheme.get("exclusion_rules")
    )

    combined = f"{eligibility}\n{exclusions}"

    rules: Dict[str, Any] = {}

    # ---------------------------------------------------------
    # STATE
    # ---------------------------------------------------------

    state = _clean(
        scheme.get("state")
    ).lower()

    if state and state not in {
        "all",
        "india",
        "central",
        "national",
        "nan",
    }:
        rules["state"] = state

    # ---------------------------------------------------------
    # STUDENT
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\bstudent\b",
            r"\bstudents\b",
            r"\bschool[- ]going\b",
            r"\bcollege[- ]going\b",
            r"\bstudying\b",
        ],
    ):
        rules["student"] = True

    # ---------------------------------------------------------
    # FARMER
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\bfarmers?\b",
            r"\bcultivators?\b",
            r"\bagricultural\s+labou?rers?\b",
            r"\btenant\s+farmers?\b",
            r"\blandless\s+farmers?\b",
        ],
    ):
        rules["occupation"] = "farmer"

    # ---------------------------------------------------------
    # WOMEN
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\bwomen\b",
            r"\bwoman\b",
            r"\bfemale\b",
            r"\bgirls?\b",
        ],
    ):
        rules["gender"] = "female"

    # ---------------------------------------------------------
    # SENIOR CITIZEN
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\bsenior\s+citizens?\b",
            r"\bold\s+age\b",
            r"\belderly\b",
        ],
    ):
        rules["age_min"] = 60

    # ---------------------------------------------------------
    # AGE LOWER BOUND
    # ---------------------------------------------------------

    age_min = _extract_number(
        r"(?:age|aged)\s*(?:of\s*)?(?:above|over|at\s+least|minimum(?:\s+age)?\s*(?:of)?)\s*(\d+)",
        eligibility,
    )

    if age_min is not None:
        rules["age_min"] = age_min

    # Examples:
    # "18 years and above"
    # "aged 18 years or above"
    # "18+"

    if "age_min" not in rules:

        age_min = _extract_number(
            r"\b(\d+)\s*(?:years?\s*)?(?:and\s*)?(?:above|or\s+above|\+)",
            eligibility,
        )

        if age_min is not None:
            rules["age_min"] = age_min

    # ---------------------------------------------------------
    # AGE UPPER BOUND
    # ---------------------------------------------------------

    age_max = _extract_number(
        r"(?:age|aged)\s*(?:of\s*)?(?:below|under|less\s+than|up\s+to|upto)\s*(\d+)",
        eligibility,
    )

    if age_max is not None:
        rules["age_max"] = age_max

    # Examples:
    # "below 60 years"
    # "up to 60 years"

    if "age_max" not in rules:

        age_max = _extract_number(
            r"\b(?:below|under|less\s+than)\s*(\d+)\s*(?:years?)?",
            eligibility,
        )

        if age_max is not None:
            rules["age_max"] = age_max

    # ---------------------------------------------------------
    # INCOME
    # ---------------------------------------------------------

    income_max = _extract_number(
        r"(?:annual\s+family\s+income|annual\s+income|family\s+income)"
        r".{0,80}?"
        r"(?:not\s+exceed|does\s+not\s+exceed|less\s+than|below|upto|up\s+to)"
        r"\s*(?:rs\.?|₹)?\s*([\d,]+)",
        eligibility,
    )

    if income_max is not None:
        rules["income_max"] = income_max

    # Common "income <= 2.5 lakh" style
    income_lakh = _extract_number(
        r"(?:income|annual\s+income|family\s+income)"
        r".{0,50}?"
        r"(?:<=|less\s+than|below|upto|up\s+to)"
        r"\s*(\d+(?:\.\d+)?)\s*lakh",
        eligibility,
    )

    if income_lakh is not None:
        rules["income_max"] = income_lakh * 100000

    # ---------------------------------------------------------
    # CASTE / CATEGORY
    # ---------------------------------------------------------

    category_patterns = {
        "sc": r"\bsc\b|\bscheduled\s+castes?\b",
        "st": r"\bst\b|\bscheduled\s+tribes?\b",
        "obc": r"\bobc\b|\bother\s+backward\s+classes?\b",
        "bc": r"\bbc\b|\bbackward\s+classes?\b",
        "ebc": r"\bebc\b|\beconomically\s+backward\b",
        "kapu": r"\bkapu\b",
        "minority": r"\bminorities?\b|\bminority\b",
    }

    detected_categories = []

    for category, pattern in category_patterns.items():

        if re.search(pattern, eligibility.lower()):
            detected_categories.append(category)

    if len(detected_categories) == 1:
        rules["caste_category"] = detected_categories[0]

    elif len(detected_categories) > 1:
        rules["caste_category"] = detected_categories

    # ---------------------------------------------------------
    # DISABILITY
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\bpersons?\s+with\s+disabilit",
            r"\bpersons?\s+with\s+disabilities",
            r"\bdisabled\s+persons?\b",
            r"\bdivyang\b",
            r"\bdisability\b",
        ],
    ):
        rules["disability"] = True

    disability_percentage = _extract_number(
        r"(\d+)\s*%\s*(?:or\s+more|and\s+above|disability)",
        eligibility,
    )

    if disability_percentage is not None:
        rules["disability_percentage_min"] = disability_percentage

    # ---------------------------------------------------------
    # LANDHOLDER
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\bland\s+owner\b",
            r"\blandowners?\b",
            r"\bland\s+holding\b",
            r"\blandholder\b",
        ],
    ):
        rules["landholder_required"] = True

    # ---------------------------------------------------------
    # TENANT FARMER
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\btenant\s+farmers?\b",
            r"\btenant\s+cultivators?\b",
        ],
    ):
        rules["tenant_farmer_allowed"] = True

    # ---------------------------------------------------------
    # LANDLESS
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\blandless\b",
            r"\blandless\s+famil",
            r"\blandless\s+households?\b",
        ],
    ):
        rules["landless_required"] = True

    # ---------------------------------------------------------
    # RATION CARD
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\bration\s+card\b",
            r"\bwhite\s+ration\s+card\b",
            r"\brice\s+card\b",
            r"\bfood\s+security\s+card\b",
        ],
    ):
        rules["ration_card_required"] = True

    # ---------------------------------------------------------
    # HOUSE OWNERSHIP
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\bhomeless\b",
            r"\bdoes\s+not\s+own\s+a\s+house\b",
            r"\bno\s+pucca\s+house\b",
            r"\bwithout\s+a\s+house\b",
        ],
    ):
        rules["owns_house"] = False

    # ---------------------------------------------------------
    # GOVERNMENT EMPLOYEE EXCLUSION
    # ---------------------------------------------------------

    if _contains(
        exclusions,
        [
            r"\bgovernment\s+employees?\b",
            r"\bstate\s+government\s+employees?\b",
            r"\bcentral\s+government\s+employees?\b",
            r"\bgovernment\s+servants?\b",
        ],
    ):
        rules["government_employee_excluded"] = True

    # ---------------------------------------------------------
    # INCOME TAX EXCLUSION
    # ---------------------------------------------------------

    if _contains(
        exclusions,
        [
            r"\bincome\s+tax\s+payers?\b",
            r"\bincome\s+tax\s+paying\b",
            r"\btax\s+payers?\b",
        ],
    ):
        rules["income_tax_payer_excluded"] = True

    # ---------------------------------------------------------
    # MARITAL STATUS
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\bwidows?\b",
            r"\bwidow\s+women\b",
        ],
    ):
        rules["marital_status"] = "widow"

    # ---------------------------------------------------------
    # CHILDREN
    # ---------------------------------------------------------

    if _contains(
        eligibility,
        [
            r"\bchildren\b",
            r"\bchild\b",
            r"\bstudents?\s+studying\b",
        ],
    ):
        rules["has_children"] = True

    return rules


def attach_structured_eligibility(
    scheme: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Return a copy of the scheme with normalized rules.
    """

    result = dict(scheme)

    result["structured_eligibility"] = (
        normalize_eligibility_rules(scheme)
    )

    return result