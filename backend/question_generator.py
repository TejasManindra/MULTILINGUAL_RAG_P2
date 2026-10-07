"""
Progressive eligibility question generator.

Converts missing eligibility-rule fields into
user-friendly questions.

This module does NOT decide eligibility.
"""

from typing import Any, Dict, List


FIELD_QUESTIONS = {

    "age":
        "What is your age?",

    "gender":
        "What is your gender?",

    "state":
        "Which state do you live in?",

    "occupation":
        "What is your occupation?",

    "student":
        "Are you currently a student?",

    "education_level":
        "What is your current education level?",

    "class_12_percentile":
        "What percentage did you score in Class 12?",

    "course_mode":
        "Are you studying in a regular, distance, or correspondence course?",

    "course_type":
        "What type of course are you pursuing?",

    "institution_recognition":
        "Is your college or institution recognized/approved as required by the scheme?",

    "family_income_annual":
        "What is your family's annual income?",

    "annual_income":
        "What is your annual income?",

    "caste_category":
        "What is your social or caste category?",

    "social_category":
        "What is your social category?",

    "religion":
        "What is your religion, if relevant to the scheme?",

    "disability":
        "Do you have a disability?",

    "disability_percentage":
        "What is your disability percentage?",

    "landholder":
        "Do you own agricultural land?",

    "land_area":
        "How much agricultural land do you own?",

    "tenant_farmer":
        "Are you a tenant farmer?",

    "landless":
        "Are you landless?",

    "ration_card":
        "Do you have a ration/rice card?",

    "owns_house":
        "Do you own a house?",

    "government_employee":
        "Are you a government employee?",

    "income_tax_payer":
        "Are you an income-tax payer?",

    "marital_status":
        "What is your marital status?",

    "has_children":
        "Do you have children?",

    "children_count":
        "How many children do you have?",

    "other_scholarship_benefit":
        "Are you currently receiving another scholarship or similar scholarship benefit?",
}


def get_missing_fields(
    evaluation: Dict[str, Any],
) -> List[str]:
    """
    Extract fields whose values are unknown.
    """

    missing = []

    for rule in evaluation.get(
        "rule_results",
        [],
    ):

        if not isinstance(
            rule,
            dict,
        ):
            continue

        if rule.get(
            "status"
        ) != "UNKNOWN":
            continue

        field = rule.get(
            "field"
        )

        if (
            field
            and field not in missing
        ):
            missing.append(
                field
            )

    return missing


def generate_questions(
    evaluation: Dict[str, Any],
    max_questions: int = 3,
) -> List[Dict[str, str]]:
    """
    Generate questions only for fields that
    are actually required by the scheme.
    """

    missing_fields = get_missing_fields(
        evaluation
    )

    questions = []

    for field in missing_fields:

        question = FIELD_QUESTIONS.get(
            field
        )

        if not question:
            question = (
                f"Please provide information "
                f"about: {field.replace('_', ' ')}."
            )

        questions.append(
            {
                "field": field,
                "question": question,
            }
        )

        if len(questions) >= max_questions:
            break

    return questions


def print_questions(
    evaluation: Dict[str, Any],
) -> None:

    questions = generate_questions(
        evaluation
    )

    print()
    print("=" * 70)
    print("ADDITIONAL INFORMATION REQUIRED")
    print("=" * 70)

    if not questions:

        print(
            "No additional questions are required."
        )

        return

    print()

    for index, item in enumerate(
        questions,
        start=1,
    ):

        print(
            f"{index}. "
            f"{item['question']}"
        )


if __name__ == "__main__":

    test_evaluation = {

        "status":
            "NEED_MORE_INFORMATION",

        "rule_results": [

            {
                "field":
                    "class_12_percentile",

                "status":
                    "PASS",
            },

            {
                "field":
                    "course_mode",

                "status":
                    "PASS",
            },

            {
                "field":
                    "course_type",

                "status":
                    "PASS",
            },

            {
                "field":
                    "institution_recognition",

                "status":
                    "UNKNOWN",
            },

            {
                "field":
                    "family_income_annual",

                "status":
                    "PASS",
            },

            {
                "field":
                    "other_scholarship_benefit",

                "status":
                    "UNKNOWN",
            },
        ],
    }

    print_questions(
        test_evaluation
    )