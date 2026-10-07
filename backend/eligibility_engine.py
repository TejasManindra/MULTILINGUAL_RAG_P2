"""
Generic deterministic eligibility engine.

Important:
- This engine does NOT use the LLM to decide eligibility.
- Unknown profile values remain unknown.
- It evaluates only structured rules that are explicitly available.
- Text-based eligibility rules are preserved for explanation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


ELIGIBLE = "ELIGIBLE"
NOT_ELIGIBLE = "NOT_ELIGIBLE"
NEED_MORE_INFORMATION = "NEED_MORE_INFORMATION"
CURRENT_STATUS_UNCONFIRMED = "CURRENT_STATUS_UNCONFIRMED"


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _is_unknown(value: Any) -> bool:
    return value is None or value == ""


def _to_number(value: Any) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        cleaned = (
            value.lower()
            .replace(",", "")
            .replace("₹", "")
            .replace("rs.", "")
            .replace("rs", "")
            .strip()
        )

        try:
            return float(cleaned)
        except ValueError:
            return None

    return None


def _matches_value(
    profile_value: Any,
    required_value: Any,
) -> Optional[bool]:
    """
    Returns:
        True  -> matches
        False -> conflicts
        None  -> cannot determine
    """

    if _is_unknown(profile_value):
        return None

    if _is_unknown(required_value):
        return None

    profile_value = _normalize(profile_value)
    required_value = _normalize(required_value)

    if isinstance(required_value, list):
        normalized_required = [_normalize(v) for v in required_value]
        return profile_value in normalized_required

    return profile_value == required_value


def _evaluate_min_max(
    value: Any,
    minimum: Any = None,
    maximum: Any = None,
) -> Optional[bool]:

    numeric_value = _to_number(value)

    if numeric_value is None:
        return None

    numeric_min = _to_number(minimum)
    numeric_max = _to_number(maximum)

    if numeric_min is not None and numeric_value < numeric_min:
        return False

    if numeric_max is not None and numeric_value > numeric_max:
        return False

    return True


def _evaluate_boolean_requirement(
    profile_value: Any,
    required_value: Any,
) -> Optional[bool]:

    if profile_value is None:
        return None

    if required_value is None:
        return None

    return bool(profile_value) == bool(required_value)


def evaluate_scheme(
    profile: Dict[str, Any],
    scheme: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate one scheme against a generic user profile.

    The scheme may contain structured rules under:
        scheme["structured_eligibility"]

    Unknown/missing rules are not treated as failures.
    """

    profile = profile or {}
    structured_rules = scheme.get("structured_eligibility") or {}

    reasons: List[str] = []
    failed_conditions: List[str] = []
    missing_information: List[str] = []

    # ---------------------------------------------------------
    # STATE
    # ---------------------------------------------------------

    required_state = structured_rules.get("state")

    if required_state:
        profile_state = profile.get("state")

        result = _matches_value(profile_state, required_state)

        if result is False:
            failed_conditions.append(
                f"State requirement: {required_state}"
            )
        elif result is None:
            missing_information.append("state")

    # ---------------------------------------------------------
    # AGE
    # ---------------------------------------------------------

    if (
        structured_rules.get("age_min") is not None
        or structured_rules.get("age_max") is not None
    ):
        result = _evaluate_min_max(
            profile.get("age"),
            structured_rules.get("age_min"),
            structured_rules.get("age_max"),
        )

        if result is False:
            failed_conditions.append("Age requirement not satisfied.")
        elif result is None:
            missing_information.append("age")

    # ---------------------------------------------------------
    # GENDER
    # ---------------------------------------------------------

    required_gender = structured_rules.get("gender")

    if required_gender:
        result = _matches_value(
            profile.get("gender"),
            required_gender,
        )

        if result is False:
            failed_conditions.append(
                f"Gender requirement: {required_gender}"
            )
        elif result is None:
            missing_information.append("gender")

    # ---------------------------------------------------------
    # OCCUPATION
    # ---------------------------------------------------------

    required_occupation = structured_rules.get("occupation")

    if required_occupation:
        result = _matches_value(
            profile.get("occupation"),
            required_occupation,
        )

        if result is False:
            failed_conditions.append(
                f"Occupation requirement: {required_occupation}"
            )
        elif result is None:
            missing_information.append("occupation")

    # ---------------------------------------------------------
    # STUDENT
    # ---------------------------------------------------------

    if structured_rules.get("student") is not None:
        result = _evaluate_boolean_requirement(
            profile.get("student"),
            structured_rules.get("student"),
        )

        if result is False:
            failed_conditions.append("Student status requirement not satisfied.")
        elif result is None:
            missing_information.append("student")

    # ---------------------------------------------------------
    # EMPLOYMENT STATUS
    # ---------------------------------------------------------

    required_employment = structured_rules.get("employment_status")

    if required_employment:
        result = _matches_value(
            profile.get("employment_status"),
            required_employment,
        )

        if result is False:
            failed_conditions.append(
                f"Employment status requirement: {required_employment}"
            )
        elif result is None:
            missing_information.append("employment_status")

    # ---------------------------------------------------------
    # EDUCATION
    # ---------------------------------------------------------

    required_education = structured_rules.get("education_level")

    if required_education:
        result = _matches_value(
            profile.get("education_level"),
            required_education,
        )

        if result is False:
            failed_conditions.append(
                f"Education requirement: {required_education}"
            )
        elif result is None:
            missing_information.append("education_level")

    # ---------------------------------------------------------
    # INCOME
    # ---------------------------------------------------------

    if structured_rules.get("income_max") is not None:

        result = _evaluate_min_max(
            profile.get("annual_income"),
            maximum=structured_rules.get("income_max"),
        )

        if result is False:
            failed_conditions.append(
                "Annual income exceeds the scheme limit."
            )
        elif result is None:
            missing_information.append("annual_income")

    # ---------------------------------------------------------
    # CASTE / SOCIAL CATEGORY
    # ---------------------------------------------------------

    required_caste = structured_rules.get("caste_category")

    if required_caste:
        result = _matches_value(
            profile.get("caste_category"),
            required_caste,
        )

        if result is False:
            failed_conditions.append(
                f"Social category requirement: {required_caste}"
            )
        elif result is None:
            missing_information.append("caste_category")

    # ---------------------------------------------------------
    # RELIGION
    # ---------------------------------------------------------

    required_religion = structured_rules.get("religion")

    if required_religion:
        result = _matches_value(
            profile.get("religion"),
            required_religion,
        )

        if result is False:
            failed_conditions.append(
                f"Religion requirement: {required_religion}"
            )
        elif result is None:
            missing_information.append("religion")

    # ---------------------------------------------------------
    # DISABILITY
    # ---------------------------------------------------------

    if structured_rules.get("disability") is not None:

        result = _evaluate_boolean_requirement(
            profile.get("disability"),
            structured_rules.get("disability"),
        )

        if result is False:
            failed_conditions.append(
                "Disability requirement not satisfied."
            )
        elif result is None:
            missing_information.append("disability")

    # Disability percentage
    if structured_rules.get("disability_percentage_min") is not None:

        result = _evaluate_min_max(
            profile.get("disability_percentage"),
            minimum=structured_rules.get(
                "disability_percentage_min"
            ),
        )

        if result is False:
            failed_conditions.append(
                "Disability percentage is below the required threshold."
            )
        elif result is None:
            missing_information.append(
                "disability_percentage"
            )

    # ---------------------------------------------------------
    # LAND
    # ---------------------------------------------------------

    if structured_rules.get("land_area_max") is not None:

        result = _evaluate_min_max(
            profile.get("land_area"),
            maximum=structured_rules.get("land_area_max"),
        )

        if result is False:
            failed_conditions.append(
                "Landholding exceeds the scheme limit."
            )
        elif result is None:
            missing_information.append("land_area")

    # Landholder requirement
    if structured_rules.get("landholder_required") is not None:

        result = _evaluate_boolean_requirement(
            profile.get("landholder"),
            structured_rules.get("landholder_required"),
        )

        if result is False:
            failed_conditions.append(
                "Landholder requirement not satisfied."
            )
        elif result is None:
            missing_information.append("landholder")

    # Tenant farmer
    if structured_rules.get("tenant_farmer_allowed") is not None:

        tenant = profile.get("tenant_farmer")

        if tenant is None:
            missing_information.append("tenant_farmer")

    # Landless
    if structured_rules.get("landless_required") is not None:

        result = _evaluate_boolean_requirement(
            profile.get("landless"),
            structured_rules.get("landless_required"),
        )

        if result is False:
            failed_conditions.append(
                "Landless-person requirement not satisfied."
            )
        elif result is None:
            missing_information.append("landless")

    # ---------------------------------------------------------
    # RATION CARD
    # ---------------------------------------------------------

    if structured_rules.get("ration_card_required") is not None:

        result = _evaluate_boolean_requirement(
            profile.get("ration_card"),
            structured_rules.get("ration_card_required"),
        )

        if result is False:
            failed_conditions.append(
                "Required ration-card condition not satisfied."
            )
        elif result is None:
            missing_information.append("ration_card")

    # ---------------------------------------------------------
    # HOUSE OWNERSHIP
    # ---------------------------------------------------------

    if structured_rules.get("owns_house") is not None:

        result = _evaluate_boolean_requirement(
            profile.get("owns_house"),
            structured_rules.get("owns_house"),
        )

        if result is False:
            failed_conditions.append(
                "House-ownership requirement not satisfied."
            )
        elif result is None:
            missing_information.append("owns_house")

    # ---------------------------------------------------------
    # GOVERNMENT EMPLOYEE EXCLUSION
    # ---------------------------------------------------------

    if structured_rules.get("government_employee_excluded"):

        value = profile.get("government_employee")

        if value is True:
            failed_conditions.append(
                "Government employees are excluded by the scheme rule."
            )
        elif value is None:
            missing_information.append(
                "government_employee"
            )

    # ---------------------------------------------------------
    # INCOME TAX EXCLUSION
    # ---------------------------------------------------------

    if structured_rules.get("income_tax_payer_excluded"):

        value = profile.get("income_tax_payer")

        if value is True:
            failed_conditions.append(
                "Income-tax payers are excluded by the scheme rule."
            )
        elif value is None:
            missing_information.append(
                "income_tax_payer"
            )

    # ---------------------------------------------------------
    # MARITAL STATUS
    # ---------------------------------------------------------

    required_marital_status = structured_rules.get(
        "marital_status"
    )

    if required_marital_status:

        result = _matches_value(
            profile.get("marital_status"),
            required_marital_status,
        )

        if result is False:
            failed_conditions.append(
                f"Marital-status requirement: {required_marital_status}"
            )
        elif result is None:
            missing_information.append("marital_status")

    # ---------------------------------------------------------
    # CHILDREN
    # ---------------------------------------------------------

    if structured_rules.get("has_children") is not None:

        result = _evaluate_boolean_requirement(
            profile.get("has_children"),
            structured_rules.get("has_children"),
        )

        if result is False:
            failed_conditions.append(
                "Children requirement not satisfied."
            )
        elif result is None:
            missing_information.append("has_children")

    # ---------------------------------------------------------
    # FINAL DECISION
    # ---------------------------------------------------------

    scheme_status = str(
        scheme.get("scheme_status", "")
    ).upper()

    if scheme_status in {
        "PROPOSED",
        "PROPOSED_UNDER_REVIEW",
        "HISTORICAL_CURRENT_CYCLE_UNCONFIRMED",
        "HISTORICAL_CURRENT_CONTINUATION_UNCONFIRMED",
    }:
        if not failed_conditions:
            return {
                "status": CURRENT_STATUS_UNCONFIRMED,
                "scheme_name": scheme.get("scheme_name"),
                "reasons": [
                    "Eligibility conditions may match, "
                    "but current implementation/payment status "
                    "is not fully confirmed."
                ],
                "failed_conditions": failed_conditions,
                "missing_information": sorted(
                    set(missing_information)
                ),
            }

    if failed_conditions:

        return {
            "status": NOT_ELIGIBLE,
            "scheme_name": scheme.get("scheme_name"),
            "reasons": reasons,
            "failed_conditions": failed_conditions,
            "missing_information": sorted(
                set(missing_information)
            ),
        }

    if missing_information:

        return {
            "status": NEED_MORE_INFORMATION,
            "scheme_name": scheme.get("scheme_name"),
            "reasons": reasons,
            "failed_conditions": [],
            "missing_information": sorted(
                set(missing_information)
            ),
        }

    return {
        "status": ELIGIBLE,
        "scheme_name": scheme.get("scheme_name"),
        "reasons": reasons,
        "failed_conditions": [],
        "missing_information": [],
    }


def evaluate_schemes(
    profile: Dict[str, Any],
    schemes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Evaluate multiple schemes against the same generic profile.
    """

    results = []

    for scheme in schemes:

        if not isinstance(scheme, dict):
            continue

        result = evaluate_scheme(
            profile=profile,
            scheme=scheme,
        )

        results.append(result)

    return results


def get_missing_information(
    evaluation: Dict[str, Any],
) -> List[str]:
    """
    Return the profile fields required to continue evaluation.
    """

    return evaluation.get(
        "missing_information",
        [],
    )