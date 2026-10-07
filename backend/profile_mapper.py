"""
Generic user-profile field mapper.

Converts common natural-language profile information
into the field names used by scheme eligibility rules.

This layer does NOT decide eligibility.
It only extracts/matches user-provided facts.
"""

from __future__ import annotations

import re
from typing import Any, Dict


# ============================================================
# PROFILE DEFAULTS
# ============================================================

PROFILE_DEFAULTS = {
    "state": None,
    "age": None,
    "gender": None,
    "occupation": None,
    "employment_status": None,
    "student": None,
    "education_level": None,

    # Academic
    "class_12_percentile": None,
    "course_mode": None,
    "course_type": None,
    "institution_recognition": None,

    # Income
    "family_income_annual": None,
    "annual_income": None,

    # Social category
    "caste_category": None,
    "social_category": None,
    "religion": None,

    # Disability
    "disability": None,
    "disability_percentage": None,

    # Agriculture
    "landholder": None,
    "land_area": None,
    "tenant_farmer": None,
    "landless": None,

    # Documents / economic status
    "ration_card": None,
    "owns_house": None,
    "government_employee": None,
    "income_tax_payer": None,

    # Family
    "marital_status": None,
    "has_children": None,
    "children_count": None,

    # Scholarship
    "other_scholarship_benefit": None,
}


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(text: str) -> str:
    """
    Normalize user query for matching.
    """

    if not text:
        return ""

    text = str(text)

    # Fix common accidental spacing problems.
    text = re.sub(
        r"\s+",
        " ",
        text.strip().lower(),
    )

    return text


# ============================================================
# NUMBER EXTRACTION
# ============================================================

def _extract_number(
    pattern: str,
    text: str,
):
    """
    Extract the first numeric capture group.
    """

    match = re.search(
        pattern,
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    try:
        return float(
            match.group(1)
        )
    except (
        ValueError,
        TypeError,
    ):
        return None


# ============================================================
# PROFILE EXTRACTION
# ============================================================

def extract_profile(
    query: str,
) -> Dict[str, Any]:
    """
    Extract user-provided facts from natural language.

    Important:
        None means UNKNOWN.

    We must never interpret an unknown field as False.
    """

    text = _normalize(query)

    profile = dict(
        PROFILE_DEFAULTS
    )

    # ========================================================
    # STATE
    # ========================================================

    if re.search(
        r"\btelangana\b|\bతెలంగాణ\b",
        text,
        re.IGNORECASE,
    ):
        profile["state"] = "telangana"

    elif re.search(
        r"\bandhra\s*pradesh\b|\bఆంధ్ర\s*ప్రదేశ్\b",
        text,
        re.IGNORECASE,
    ):
        profile["state"] = "andhra_pradesh"

    # ========================================================
    # STUDENT
    # ========================================================

    if re.search(
        r"\bstudent\b"
        r"|\bstudents\b"
        r"|\bstudent\s+from\b"
        r"|\bstudying\b"
        r"|\bcollege student\b"
        r"|\buniversity student\b"
        r"|\bundergraduate\b"
        r"|\bpostgraduate\b"
        r"|\bచదువుతున్న\b"
        r"|\bవిద్యార్థి\b"
        r"|\bవిద్యార్థిని\b",
        text,
        re.IGNORECASE,
    ):
        profile["student"] = True

    # ========================================================
    # GENDER
    # ========================================================

    if re.search(
        r"\bwoman\b"
        r"|\bwomen\b"
        r"|\bfemale\b"
        r"|\bgirl\b"
        r"|\blady\b"
        r"|\bమహిళ\b"
        r"|\bస్త్రీ\b",
        text,
        re.IGNORECASE,
    ):
        profile["gender"] = "female"

    elif re.search(
        r"\bman\b"
        r"|\bmale\b"
        r"|\bboy\b"
        r"|\bపురుషుడు\b",
        text,
        re.IGNORECASE,
    ):
        profile["gender"] = "male"

    # ========================================================
    # OCCUPATION
    # ========================================================

    if re.search(
        r"\bfarmer\b"
        r"|\bfarmers\b"
        r"|\bcultivator\b"
        r"|\bagricultural worker\b"
        r"|\bagricultural labourer\b"
        r"|\btenant farmer\b"
        r"|\btenant cultivator\b"
        r"|\bరైతు\b"
        r"|\bవ్యవసాయదారుడు\b",
        text,
        re.IGNORECASE,
    ):
        profile["occupation"] = "farmer"

    elif re.search(
        r"\bunemployed\b"
        r"|\bjobless\b"
        r"|\bjob seeker\b"
        r"|\bwithout a job\b"
        r"|\bనిరుద్యోగి\b",
        text,
        re.IGNORECASE,
    ):
        profile["occupation"] = "unemployed"
        profile["employment_status"] = "unemployed"

    # ========================================================
    # SENIOR CITIZEN
    # ========================================================

    if re.search(
        r"\bsenior citizen\b"
        r"|\belderly\b"
        r"|\bold age\b"
        r"|\bవృద్ధ\b",
        text,
        re.IGNORECASE,
    ):
        profile["occupation"] = "senior_citizen"

    # ========================================================
    # AGE
    # ========================================================

    age = _extract_number(
        r"\b(?:age|aged)"
        r"\s*(?:is|:)?\s*"
        r"(\d{1,3})\b",
        text,
    )

    if age is None:

        age = _extract_number(
            r"\b(\d{1,3})\s*"
            r"(?:years?\s*old|year\s*old|వయస్సు)\b",
            text,
        )

    if age is not None:
        profile["age"] = int(age)

    # ========================================================
    # CLASS 12 PERCENTAGE
    # ========================================================

    percentage = _extract_number(
        r"(?:class\s*12|12th|intermediate|inter)"
        r".{0,30}?"
        r"(\d+(?:\.\d+)?)\s*%",
        text,
    )

    if percentage is None:

        percentage = _extract_number(
            r"(\d+(?:\.\d+)?)\s*%"
            r"\s*(?:in\s*)?"
            r"(?:class\s*12|12th|intermediate|inter)",
            text,
        )

    if percentage is not None:
        profile[
            "class_12_percentile"
        ] = percentage

    # ========================================================
    # FAMILY / ANNUAL INCOME
    # ========================================================

    income_lakh = _extract_number(
        r"(?:family\s+income"
        r"|annual\s+income"
        r"|family\s+annual\s+income"
        r"|income)"
        r".{0,40}?"
        r"(?:₹|rs\.?|rs)?\s*"
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:lakh|lakhs|lac|lacs)",
        text,
    )

    if income_lakh is not None:

        income = (
            income_lakh * 100000
        )

        profile[
            "family_income_annual"
        ] = income

        profile[
            "annual_income"
        ] = income

    else:

        income = _extract_number(
            r"(?:family\s+income"
            r"|annual\s+income"
            r"|family\s+annual\s+income"
            r"|income)"
            r".{0,30}?"
            r"(?:₹|rs\.?|rs)?\s*"
            r"([\d,]+)",
            text,
        )

        if income is not None:

            income = float(
                str(income)
                .replace(",", "")
            )

            profile[
                "family_income_annual"
            ] = income

            profile[
                "annual_income"
            ] = income

    # ========================================================
    # COURSE MODE
    # ========================================================
    #
    # Important improvement:
    #
    # The previous mapper only detected:
    #   "regular course"
    #   "regular student"
    #
    # It did NOT reliably detect:
    #   "regular degree course"
    #   "regular degree"
    #   "studying a regular course"
    #
    # We now detect the concept of regular study
    # independently from course type.
    # ========================================================

    if re.search(
        r"\bregular\b"
        r"(?:\s+(?:course|degree|program|programme|study|studies|education|college|university))?",
        text,
        re.IGNORECASE,
    ):
        profile[
            "course_mode"
        ] = "regular"

    elif re.search(
        r"\b(distance|correspondence)\b",
        text,
        re.IGNORECASE,
    ):
        mode_match = re.search(
            r"\b(distance|correspondence)\b",
            text,
            re.IGNORECASE,
        )

        if mode_match:

            mode = (
                mode_match.group(1)
                .lower()
            )

            profile[
                "course_mode"
            ] = mode

    # ========================================================
    # COURSE TYPE
    # ========================================================

    if re.search(
        r"\bdiploma\b"
        r"|\bpolytechnic\b"
        r"|\biti\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "course_type"
        ] = "diploma"

    elif re.search(
        r"\bdegree\b"
        r"|\bgraduation\b"
        r"|\bundergraduate degree\b"
        r"|\bgraduate degree\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "course_type"
        ] = "degree"

    elif re.search(
        r"\bpostgraduate\b"
        r"|\bpost graduate\b"
        r"|\bpg course\b"
        r"|\bmaster'?s\b"
        r"|\bm\.?tech\b"
        r"|\bm\.?sc\b"
        r"|\bmba\b"
        r"|\bmca\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "course_type"
        ] = "postgraduate"

    # ========================================================
    # EDUCATION LEVEL
    # ========================================================

    if re.search(
        r"\bclass\s*12\b"
        r"|\b12th\b"
        r"|\bintermediate\b"
        r"|\binter\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "education_level"
        ] = "class_12"

    elif re.search(
        r"\bpostgraduate\b"
        r"|\bpost graduate\b"
        r"|\bmaster'?s\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "education_level"
        ] = "postgraduate"

    elif re.search(
        r"\bdegree\b"
        r"|\bundergraduate\b"
        r"|\bgraduation\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "education_level"
        ] = "undergraduate"

    # ========================================================
    # INSTITUTION RECOGNITION
    # ========================================================

    if re.search(
        r"\brecognized\s+(?:college|institution|university)\b"
        r"|\brecognised\s+(?:college|institution|university)\b"
        r"|\bgovernment\s+recognized\b"
        r"|\bgovernment\s+recognised\b"
        r"|\bugc\s+recognized\b"
        r"|\bugc\s+recognised\b"
        r"|\bapproved\s+(?:college|institution|university)\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "institution_recognition"
        ] = True

    elif re.search(
        r"\bunrecognized\s+(?:college|institution|university)\b"
        r"|\bunrecognised\s+(?:college|institution|university)\b"
        r"|\bnot\s+recognized\b"
        r"|\bnot\s+recognised\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "institution_recognition"
        ] = False

    # ========================================================
    # CASTE / SOCIAL CATEGORY
    # ========================================================

    category_patterns = {

        "sc": (
            r"\bsc\b"
            r"|\bscheduled caste\b"
        ),

        "st": (
            r"\bst\b"
            r"|\bscheduled tribe\b"
        ),

        "bc": (
            r"\bbc\b"
            r"|\bbackward class\b"
        ),

        "ebc": (
            r"\bebc\b"
            r"|\beconomically backward\b"
        ),

        "obc": (
            r"\bobc\b"
            r"|\bother backward class\b"
        ),

        "minority": (
            r"\bminority\b"
            r"|\bminorities\b"
        ),

        "kapu": (
            r"\bkapu\b"
        ),
    }

    for category, pattern in (
        category_patterns.items()
    ):

        if re.search(
            pattern,
            text,
            re.IGNORECASE,
        ):

            profile[
                "caste_category"
            ] = category

            profile[
                "social_category"
            ] = category

            break

    # ========================================================
    # RELIGION
    # ========================================================

    religion_patterns = {
        "muslim": (
            r"\bmuslim\b"
            r"|\bislam\b"
        ),

        "christian": (
            r"\bchristian\b"
            r"|\bchristianity\b"
        ),

        "hindu": (
            r"\bhindu\b"
            r"|\bhinduism\b"
        ),

        "sikh": (
            r"\bsikh\b"
            r"|\bsikhism\b"
        ),
    }

    for religion, pattern in (
        religion_patterns.items()
    ):

        if re.search(
            pattern,
            text,
            re.IGNORECASE,
        ):

            profile[
                "religion"
            ] = religion

            break

    # ========================================================
    # DISABILITY
    # ========================================================

    if re.search(
        r"\bdisabled\b"
        r"|\bdisability\b"
        r"|\bperson with disability\b"
        r"|\bdivyang\b"
        r"|\bవికలాంగ\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "disability"
        ] = True

    disability_percentage = _extract_number(
        r"(\d+(?:\.\d+)?)\s*%"
        r"\s*(?:disability|disabled)",
        text,
    )

    if disability_percentage is not None:

        profile[
            "disability_percentage"
        ] = disability_percentage

        profile[
            "disability"
        ] = True

    # ========================================================
    # LANDLESS
    # ========================================================

    if re.search(
        r"\blandless\b"
        r"|\bno land\b"
        r"|\blandless farmer\b"
        r"|\blandless labourer\b"
        r"|\blandless laborer\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "landless"
        ] = True

    # ========================================================
    # TENANT FARMER
    # ========================================================

    if re.search(
        r"\btenant farmer\b"
        r"|\btenant cultivator\b"
        r"|\btenant agricultural\b",
        text,
        re.IGNORECASE,
    ):

        profile[
            "tenant_farmer"
        ] = True

        profile[
            "occupation"
        ] = "farmer"

    # ========================================================
    # LAND AREA
    # ========================================================

    land_area = _extract_number(
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:acres?|acre)\b",
        text,
    )

    if land_area is not None:

        profile[
            "land_area"
        ] = land_area

        profile[
            "landholder"
        ] = True

    # ========================================================
    # RATION CARD
    # ========================================================

    if re.search(
        r"\bwhite ration card\b"
        r"|\bration card\b"
        r"|\brice card\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "ration_card"
        ] = True

    # ========================================================
    # GOVERNMENT EMPLOYEE
    # ========================================================

    if re.search(
        r"\bgovernment employee\b"
        r"|\bgovt employee\b"
        r"|\bgovernment servant\b"
        r"|\bgovernment job\b"
        r"|\bworking for government\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "government_employee"
        ] = True

    # ========================================================
    # INCOME TAX PAYER
    # ========================================================

    if re.search(
        r"\bincome tax payer\b"
        r"|\bincome-tax payer\b"
        r"|\bpay income tax\b"
        r"|\bit payer\b"
        r"|\bfile income tax\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "income_tax_payer"
        ] = True

    # ========================================================
    # HOUSE OWNERSHIP
    # ========================================================

    if re.search(
        r"\bdo not own a house\b"
        r"|\bdon't own a house\b"
        r"|\bdo not have a house\b"
        r"|\bdon't have a house\b"
        r"|\bno house\b"
        r"|\bhomeless\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "owns_house"
        ] = False

    elif re.search(
        r"\bown a house\b"
        r"|\bowns a house\b"
        r"|\bhave my own house\b"
        r"|\bown my house\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "owns_house"
        ] = True

    # ========================================================
    # MARITAL STATUS
    # ========================================================

    if re.search(
        r"\bwidow\b"
        r"|\bwidowed\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "marital_status"
        ] = "widow"

    elif re.search(
        r"\bmarried\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "marital_status"
        ] = "married"

    elif re.search(
        r"\bunmarried\b"
        r"|\bsingle\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "marital_status"
        ] = "single"

    # ========================================================
    # CHILDREN
    # ========================================================

    if re.search(
        r"\bmy child\b"
        r"|\bmy children\b"
        r"|\bhave children\b"
        r"|\bhas children\b"
        r"|\bparent\b"
        r"|\bmother of\b"
        r"|\bfather of\b",
        text,
        re.IGNORECASE,
    ):
        profile[
            "has_children"
        ] = True

    children_count = _extract_number(
        r"\b(\d+)\s+children\b",
        text,
    )

    if children_count is None:

        children_count = _extract_number(
            r"\b(\d+)\s+kids\b",
            text,
        )

    if children_count is not None:

        profile[
            "children_count"
        ] = int(
            children_count
        )

        profile[
            "has_children"
        ] = True

    # ========================================================
    # OTHER SCHOLARSHIP BENEFIT
    # ========================================================

    if re.search(
        r"\balready receiving.*scholarship\b"
        r"|\breceiving another scholarship\b"
        r"|\bgetting another scholarship\b"
        r"|\bcurrently receiving a scholarship\b"
        r"|\bother scholarship\b",
        text,
        re.IGNORECASE,
    ):

        profile[
            "other_scholarship_benefit"
        ] = True

    # Explicit negative statements.
    elif re.search(
        r"\bnot receiving any scholarship\b"
        r"|\bnot receiving another scholarship\b"
        r"|\bno other scholarship\b"
        r"|\bnot getting any other scholarship\b",
        text,
        re.IGNORECASE,
    ):

        profile[
            "other_scholarship_benefit"
        ] = False

    return profile


# ============================================================
# COMPACT PROFILE
# ============================================================

def compact_profile(
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Remove unknown fields for display/logging.
    """

    return {
        key: value
        for key, value in profile.items()
        if value is not None
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_queries = [

        (
            "I am a student from Telangana. "
            "I got 85% in 12th and my family income "
            "is 3 lakhs. I am studying a regular "
            "degree course. Can I get a scholarship?"
        ),

        (
            "I am a 45 year old woman farmer "
            "from Telangana with a white ration card."
        ),

        (
            "I am an SC student studying a regular "
            "degree course in a government recognized "
            "college. My family income is 2 lakhs."
        ),

        (
            "I am a tenant farmer from Andhra Pradesh "
            "with 3 acres of land."
        ),

        (
            "I am a person with 40% disability "
            "and I do not own a house."
        ),

        (
            "I am currently receiving another scholarship."
        ),
    ]

    for query in test_queries:

        print()
        print("=" * 80)
        print("QUERY:")
        print(query)
        print("-" * 80)

        profile = extract_profile(
            query
        )

        print(
            compact_profile(profile)
        )