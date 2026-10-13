import re
from typing import Any, Dict


# ============================================================
# HELPERS
# ============================================================

def _normalize(text: Any) -> str:
    if text is None:
        return ""

    text = str(text).strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text


def _first_match(
    text: str,
    patterns,
):
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return match

    return None


def _extract_number(
    text: str,
    patterns,
):
    match = _first_match(
        text,
        patterns,
    )

    if not match:
        return None

    try:
        return float(
            match.group(1)
            .replace(",", "")
        )
    except Exception:
        return None


# ============================================================
# STATE
# ============================================================

def _extract_state(text: str):
    normalized = _normalize(text)

    if re.search(
        r"\btelangana\b|\bts\b|తెలంగాణ",
        normalized,
        re.IGNORECASE,
    ):
        return "telangana"

    if re.search(
        r"\bandhra pradesh\b|\bandhra\b|\bap\b|ఆంధ్రప్రదేశ్|ఆంధ్ర",
        normalized,
        re.IGNORECASE,
    ):
        return "andhra_pradesh"

    return None


# ============================================================
# OCCUPATION
# ============================================================

def _extract_occupation(text: str):
    normalized = _normalize(text)

    if re.search(
        r"\btenant\s+farmer\b"
        r"|\btenant\s+cultivator\b"
        r"|\bsharecropper\b"
        r"|\bfarmer\b"
        r"|\bfarming\b"
        r"|\bcultivator\b"
        r"|\bkisan\b"
        r"|\brythu\b"
        r"|రైతు"
        r"|వ్యవసాయం",
        normalized,
        re.IGNORECASE,
    ):
        return "farmer"

    if re.search(
        r"\bstudent\b"
        r"|\bstudying\b"
        r"|\bcollege student\b"
        r"|\buniversity student\b"
        r"|విద్యార్థి",
        normalized,
        re.IGNORECASE,
    ):
        return "student"

    if re.search(
        r"\bunemployed\b"
        r"|\bjobless\b"
        r"|\bnot working\b"
        r"|నిరుద్యోగి",
        normalized,
        re.IGNORECASE,
    ):
        return "unemployed"

    return None


# ============================================================
# FARMER STATUS
# ============================================================

def _extract_tenant_farmer(text: str):
    return bool(
        re.search(
            r"\btenant\s+farmer\b"
            r"|\btenant\s+cultivator\b"
            r"|\bsharecropper\b"
            r"|\bshare\s+cropper\b"
            r"|\boral\s+lessee\b"
            r"|\btenant\b.*\bfarmer\b"
            r"|కౌలు రైతు"
            r"|కౌలు రైతులు"
            r"|భాగస్వామ్య రైతు",
            text,
            re.IGNORECASE,
        )
    )


def _extract_landholder(text: str):
    """
    IMPORTANT:
    Do not infer ownership from acreage.

    "I cultivate 2 acres" != "I own 2 acres".
    """

    return bool(
        re.search(
            r"\bi\s+own\s+\d+(?:\.\d+)?\s+acres?\b"
            r"|\bi\s+own\s+\d+(?:\.\d+)?\s+acre\b"
            r"|\bi\s+am\s+a\s+landowner\b"
            r"|\bi\s+am\s+a\s+land\s+owner\b"
            r"|\bi\s+own\s+agricultural\s+land\b"
            r"|\bi\s+own\s+farmland\b"
            r"|\blandowner\b"
            r"|\bland\s+owner\b"
            r"|నేను భూమి యజమాని"
            r"|నా భూమి",
            text,
            re.IGNORECASE,
        )
    )


def _extract_land_area(text: str):
    patterns = [
        r"\b(\d+(?:\.\d+)?)\s*acres?\b",
        r"\b(\d+(?:\.\d+)?)\s*acre\b",
        r"\b(\d+(?:\.\d+)?)\s*ఎకరాలు?\b",
    ]

    return _extract_number(
        text,
        patterns,
    )


# ============================================================
# INCOME
# ============================================================

def _extract_income(text: str):
    patterns = [
        r"(?:family\s+income|annual\s+family\s+income)"
        r"\s*(?:is|of|around|about|:)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
        r"\s*(lakh|lakhs|lacs|lac)?",

        r"(?:annual\s+income|yearly\s+income|income)"
        r"\s*(?:is|of|around|about|:)?\s*₹?\s*([\d,]+(?:\.\d+)?)"
        r"\s*(lakh|lakhs|lacs|lac)?",

        r"₹\s*([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|lacs|lac)?",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if not match:
            continue

        try:
            amount = float(
                match.group(1).replace(",", "")
            )
        except Exception:
            continue

        unit = (
            match.group(2)
            or ""
        ).lower()

        if unit in {
            "lakh",
            "lakhs",
            "lac",
            "lacs",
        }:
            amount *= 100000

        return amount

    return None


# ============================================================
# AGE
# ============================================================

def _extract_age(text: str):
    return _extract_number(
        text,
        [
            r"\b(\d{1,3})\s*(?:years?\s*old|year\s*old)\b",
            r"\bage\s*(?:is|:)?\s*(\d{1,3})\b",
        ],
    )


# ============================================================
# GENDER
# ============================================================

def _extract_gender(text: str):
    normalized = _normalize(text)

    if re.search(
        r"\bmale\b|\bman\b|\bboy\b|పురుషుడు|పురుష",
        normalized,
        re.IGNORECASE,
    ):
        return "male"

    if re.search(
        r"\bfemale\b|\bwoman\b|\bgirl\b|మహిళ|స్త్రీ",
        normalized,
        re.IGNORECASE,
    ):
        return "female"

    return None


# ============================================================
# STUDENT
# ============================================================

def _extract_student(text: str):
    normalized = _normalize(text)

    if re.search(
        r"\bstudent\b"
        r"|\bstudying\b"
        r"|\bpursuing\b"
        r"|\bcollege\b"
        r"|\buniversity\b"
        r"|విద్యార్థి"
        r"|చదువుతున్న",
        normalized,
        re.IGNORECASE,
    ):
        return True

    return None


# ============================================================
# EDUCATION
# ============================================================

def _extract_education_level(text: str):
    normalized = _normalize(text)

    if re.search(
        r"\b12th\b"
        r"|\bclass\s*12\b"
        r"|\b12th\s+class\b"
        r"|\bintermediate\b"
        r"|\binter\b",
        normalized,
        re.IGNORECASE,
    ):
        return "class_12"

    if re.search(
        r"\bdegree\b"
        r"|\bgraduation\b"
        r"\bgraduate\b"
        r"|\bbachelor\b"
        r"|\bundergraduate\b",
        normalized,
        re.IGNORECASE,
    ):
        return "degree"

    if re.search(
        r"\bdiploma\b",
        normalized,
        re.IGNORECASE,
    ):
        return "diploma"

    return None


# ============================================================
# CLASS 12 PERCENTAGE
# ============================================================

def _extract_class_12_percentage(text: str):
    patterns = [
        r"\b(?:class\s*12|12th)\b"
        r".{0,50}?"
        r"\b(\d+(?:\.\d+)?)\s*%",

        r"\b(\d+(?:\.\d+)?)\s*%"
        r".{0,50}?"
        r"\b(?:class\s*12|12th)\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            try:
                return float(
                    match.group(1)
                )
            except Exception:
                return None

    return None


# ============================================================
# COURSE TYPE
# ============================================================

def _extract_course_type(text: str):
    normalized = _normalize(text)

    if re.search(
        r"\bdegree\b"
        r"|\bbachelor\b"
        r"|\bgraduation\b"
        r"|\bundergraduate\b",
        normalized,
        re.IGNORECASE,
    ):
        return "degree"

    if re.search(
        r"\bdiploma\b",
        normalized,
        re.IGNORECASE,
    ):
        return "diploma"

    return None


# ============================================================
# COURSE MODE
# ============================================================

def _extract_course_mode(text: str):
    normalized = _normalize(text)

    if re.search(
        r"\bregular\b"
        r"(?:\s+(?:course|degree|program|programme|study|studies|education|college|university))?",
        normalized,
        re.IGNORECASE,
    ):
        return "regular"

    if re.search(
        r"\bdistance\b"
        r"|\bdistance\s+education\b",
        normalized,
        re.IGNORECASE,
    ):
        return "distance"

    if re.search(
        r"\bcorrespondence\b",
        normalized,
        re.IGNORECASE,
    ):
        return "correspondence"

    return None


# ============================================================
# OTHER SCHOLARSHIP
# ============================================================

def _extract_other_scholarship(text: str):
    normalized = _normalize(text)

    if re.search(
        r"\breceiving\s+(?:another\s+)?scholarship\b"
        r"|\bother\s+scholarship\b"
        r"|\balready\s+getting\s+scholarship\b",
        normalized,
        re.IGNORECASE,
    ):
        return True

    if re.search(
        r"\bnot\s+receiving\s+(?:any\s+)?(?:other\s+)?scholarship\b"
        r"|\bno\s+other\s+scholarship\b",
        normalized,
        re.IGNORECASE,
    ):
        return False

    return None


# ============================================================
# DISABILITY
# ============================================================

def _extract_disability(text: str):
    normalized = _normalize(text)

    if re.search(
        r"\bdisabled\b"
        r"|\bdisability\b"
        r"|\bdivyang\b"
        r"|\bpwd\b"
        r"|దివ్యాంగ"
        r"|వైకల్యం",
        normalized,
        re.IGNORECASE,
    ):
        return True

    return None


# ============================================================
# MAIN PROFILE EXTRACTION
# ============================================================

def extract_profile(
    text: str,
) -> Dict[str, Any]:

    text = text or ""

    profile: Dict[str, Any] = {}

    # --------------------------------------------------------
    # Basic
    # --------------------------------------------------------

    state = _extract_state(text)

    if state:
        profile["state"] = state

    age = _extract_age(text)

    if age is not None:
        profile["age"] = age

    gender = _extract_gender(text)

    if gender:
        profile["gender"] = gender

    occupation = _extract_occupation(text)

    if occupation:
        profile["occupation"] = occupation

    student = _extract_student(text)

    if student is not None:
        profile["student"] = student

    # --------------------------------------------------------
    # Farmer
    # --------------------------------------------------------

    tenant_farmer = _extract_tenant_farmer(
        text
    )

    landholder = _extract_landholder(
        text
    )

    land_area = _extract_land_area(
        text
    )

    if tenant_farmer:
        profile["tenant_farmer"] = True
        profile["landholder"] = False

    elif landholder:
        profile["landholder"] = True
        profile["tenant_farmer"] = False

    if land_area is not None:
        profile["land_area"] = land_area

    if (
        occupation == "farmer"
        and "tenant_farmer" not in profile
    ):
        profile["tenant_farmer"] = None

    # --------------------------------------------------------
    # Income
    # --------------------------------------------------------

    income = _extract_income(text)

    if income is not None:
        profile["family_income_annual"] = income
        profile["annual_income"] = income

    # --------------------------------------------------------
    # Education
    # --------------------------------------------------------

    education_level = _extract_education_level(
        text
    )

    if education_level:
        profile["education_level"] = education_level

    class_12_percentage = (
        _extract_class_12_percentage(text)
    )

    if class_12_percentage is not None:
        profile["class_12_percentile"] = (
            class_12_percentage
        )

    course_type = _extract_course_type(
        text
    )

    if course_type:
        profile["course_type"] = course_type

    course_mode = _extract_course_mode(
        text
    )

    if course_mode:
        profile["course_mode"] = course_mode

    # --------------------------------------------------------
    # Other
    # --------------------------------------------------------

    other_scholarship = (
        _extract_other_scholarship(text)
    )

    if other_scholarship is not None:
        profile[
            "other_scholarship_benefit"
        ] = other_scholarship

    disability = _extract_disability(
        text
    )

    if disability is not None:
        profile["disability"] = disability

    # --------------------------------------------------------
    # Final consistency
    # --------------------------------------------------------

    # A tenant farmer is NOT automatically a landowner.
    if profile.get("tenant_farmer") is True:
        profile["landholder"] = False

    return profile


# ============================================================
# COMPACT PROFILE
# ============================================================

def compact_profile(
    profile: Dict[str, Any],
) -> Dict[str, Any]:

    if not profile:
        return {}

    return {
        key: value
        for key, value in profile.items()
        if value is not None
    }