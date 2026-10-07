from typing import Any, Dict, List


PASS = "PASS"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"
DOCUMENTED_ONLY = "DOCUMENTED_ONLY"
UNSUPPORTED = "UNSUPPORTED"


SUPPORTED_OPERATORS = {
    "equals",
    "not_equals",
    "greater_than",
    "greater_than_or_equal",
    "less_than",
    "less_than_or_equal",
    "in",
    "not_in",
}


def _normalize(value: Any) -> Any:

    if isinstance(value, str):
        return value.strip().lower()

    return value


def _compare(
    actual: Any,
    operator: str,
    expected: Any,
) -> str:

    if actual is None:
        return UNKNOWN

    actual_n = _normalize(actual)
    expected_n = _normalize(expected)

    try:

        if operator == "equals":
            return (
                PASS
                if actual_n == expected_n
                else FAIL
            )

        if operator == "not_equals":
            return (
                PASS
                if actual_n != expected_n
                else FAIL
            )

        if operator == "greater_than":
            return (
                PASS
                if actual_n > expected_n
                else FAIL
            )

        if operator == "greater_than_or_equal":
            return (
                PASS
                if actual_n >= expected_n
                else FAIL
            )

        if operator == "less_than":
            return (
                PASS
                if actual_n < expected_n
                else FAIL
            )

        if operator == "less_than_or_equal":
            return (
                PASS
                if actual_n <= expected_n
                else FAIL
            )

        if operator == "in":

            if not isinstance(
                expected_n,
                (list, tuple, set),
            ):
                return UNSUPPORTED

            return (
                PASS
                if actual_n in [
                    _normalize(x)
                    for x in expected_n
                ]
                else FAIL
            )

        if operator == "not_in":

            if not isinstance(
                expected_n,
                (list, tuple, set),
            ):
                return UNSUPPORTED

            return (
                PASS
                if actual_n not in [
                    _normalize(x)
                    for x in expected_n
                ]
                else FAIL
            )

    except (
        TypeError,
        ValueError,
    ):
        return UNSUPPORTED

    return UNSUPPORTED


def evaluate_rule(
    rule: Dict[str, Any],
    profile: Dict[str, Any],
) -> Dict[str, Any]:

    field = rule.get(
        "field"
    )

    operator = str(
        rule.get(
            "operator",
            ""
        )
    ).strip().lower()

    expected = rule.get(
        "value"
    )

    condition_group = rule.get(
        "condition_group"
    )

    source = rule.get(
        "source"
    )

    actual = profile.get(
        field
    )

    # ========================================================
    # DOCUMENTED REQUIREMENT
    # ========================================================

    if operator in {
        "documented_requirement",
        "documented",
        "descriptive",
        "requirement",
    }:

        return {
            "field": field,
            "operator": operator,
            "expected": expected,
            "actual": actual,
            "status": DOCUMENTED_ONLY,
            "condition_group": condition_group,
            "source": source,
            "reason": (
                "This requirement is documented in "
                "the source but is not represented "
                "as a machine-evaluable rule."
            ),
        }

    # ========================================================
    # MISSING FIELD
    # ========================================================

    if field is None:

        return {
            "field": None,
            "operator": operator,
            "expected": expected,
            "actual": actual,
            "status": UNSUPPORTED,
            "condition_group": condition_group,
            "source": source,
            "reason": (
                "Rule does not specify a field."
            ),
        }

    # ========================================================
    # UNKNOWN OPERATOR
    # ========================================================

    if operator not in SUPPORTED_OPERATORS:

        return {
            "field": field,
            "operator": operator,
            "expected": expected,
            "actual": actual,
            "status": UNSUPPORTED,
            "condition_group": condition_group,
            "source": source,
            "reason": (
                "Operator is not currently "
                "supported by the deterministic evaluator."
            ),
        }

    # ========================================================
    # MACHINE EVALUATION
    # ========================================================

    status = _compare(
        actual,
        operator,
        expected,
    )

    return {
        "field": field,
        "operator": operator,
        "expected": expected,
        "actual": actual,
        "status": status,
        "condition_group": condition_group,
        "source": source,
        "reason": None,
    }


def _deduplicate_rules(
    rules: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    unique = []
    seen = set()

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        key = (
            rule.get("field"),
            rule.get("operator"),
            repr(rule.get("value")),
            rule.get("condition_group"),
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(rule)

    return unique


def evaluate_scheme_rules(
    scheme: Dict[str, Any],
    profile: Dict[str, Any],
) -> Dict[str, Any]:

    scheme_name = scheme.get(
        "scheme_name"
    )

    scheme_id = scheme.get(
        "scheme_id"
    )

    raw_rules = scheme.get(
        "eligibility_rules",
        []
    )

    if not isinstance(
        raw_rules,
        list,
    ):
        raw_rules = []

    rules = _deduplicate_rules(
        raw_rules
    )

    # ========================================================
    # NO STRUCTURED RULES
    # ========================================================

    if not rules:

        return {
            "status": "RULES_REQUIRE_REVIEW",
            "scheme_name": scheme_name,
            "scheme_id": scheme_id,
            "rule_results": [],
            "reason": (
                "No structured eligibility rules "
                "are available for deterministic evaluation."
            ),
        }

    # ========================================================
    # EVALUATE
    # ========================================================

    rule_results = [
        evaluate_rule(
            rule,
            profile,
        )
        for rule in rules
    ]

    # ========================================================
    # HARD FAILURE
    # ========================================================

    failed = [
        result
        for result in rule_results
        if result["status"] == FAIL
    ]

    if failed:

        return {
            "status": "NOT_ELIGIBLE",
            "scheme_name": scheme_name,
            "scheme_id": scheme_id,
            "rule_results": rule_results,
            "reason": (
                "One or more machine-evaluable "
                "eligibility conditions failed."
            ),
        }

    # ========================================================
    # MISSING INFORMATION
    # ========================================================

    unknown = [
        result
        for result in rule_results
        if result["status"] == UNKNOWN
    ]

    if unknown:

        return {
            "status": "NEED_MORE_INFORMATION",
            "scheme_name": scheme_name,
            "scheme_id": scheme_id,
            "rule_results": rule_results,
            "reason": (
                "One or more machine-evaluable "
                "conditions require additional user information."
            ),
        }

    # ========================================================
    # UNSUPPORTED RULES
    # ========================================================

    unsupported = [
        result
        for result in rule_results
        if result["status"] == UNSUPPORTED
    ]

    if unsupported:

        return {
            "status": "RULES_REQUIRE_REVIEW",
            "scheme_name": scheme_name,
            "scheme_id": scheme_id,
            "rule_results": rule_results,
            "reason": (
                "Some eligibility rules cannot currently "
                "be evaluated deterministically."
            ),
        }

    # ========================================================
    # DOCUMENTED-ONLY RULES
    # ========================================================

    documented = [
        result
        for result in rule_results
        if result["status"] == DOCUMENTED_ONLY
    ]

    # If all rules are descriptive, do NOT say eligible.
    if len(documented) == len(rule_results):

        return {
            "status": "RULES_REQUIRE_REVIEW",
            "scheme_name": scheme_name,
            "scheme_id": scheme_id,
            "rule_results": rule_results,
            "reason": (
                "Eligibility requirements are documented "
                "but are not sufficiently structured for "
                "a deterministic eligibility decision."
            ),
        }

    # Some machine rules passed and some descriptive
    # requirements remain.
    if documented:

        return {
            "status": "RULES_REQUIRE_REVIEW",
            "scheme_name": scheme_name,
            "scheme_id": scheme_id,
            "rule_results": rule_results,
            "reason": (
                "All machine-evaluable conditions passed, "
                "but additional documented requirements "
                "cannot be deterministically verified."
            ),
        }

    # ========================================================
    # ALL MACHINE RULES PASSED
    # ========================================================

    return {
        "status": "ELIGIBLE",
        "scheme_name": scheme_name,
        "scheme_id": scheme_id,
        "rule_results": rule_results,
        "reason": (
            "All available machine-evaluable "
            "eligibility conditions passed."
        ),
    }


def evaluate_multiple_schemes(
    schemes: List[Dict[str, Any]],
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return [
        evaluate_scheme_rules(
            scheme,
            profile,
        )
        for scheme in schemes
    ]


if __name__ == "__main__":

    # ========================================================
    # BASIC TEST
    # ========================================================

    test_scheme = {
        "scheme_id": "TEST001",
        "scheme_name": "Test Student Scheme",

        "eligibility_rules": [

            {
                "field": "age",
                "operator": "greater_than_or_equal",
                "value": 18,
            },

            {
                "field": "student",
                "operator": "equals",
                "value": True,
            },

            {
                "field": "family_income_annual",
                "operator": "less_than_or_equal",
                "value": 450000,
            },

            {
                "field": "category",
                "operator": "documented_requirement",
                "value": "Applicable categories as per scheme guidelines",
            },
        ],
    }

    profile = {
        "age": 20,
        "student": True,
        "family_income_annual": 300000,
    }

    result = evaluate_scheme_rules(
        test_scheme,
        profile,
    )

    print("\nTEST RESULT")
    print("=" * 60)

    print(
        "Status:",
        result["status"],
    )

    for rule in result["rule_results"]:

        print(
            rule["field"],
            "=>",
            rule["status"],
        )