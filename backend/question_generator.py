from typing import Any, Dict, List


# ============================================================
# HUMAN-READABLE QUESTIONS
# ============================================================

FIELD_QUESTIONS = {

    "age":
        "What is your age?",

    "gender":
        "What is your gender?",

    "state":
        "Which state do you currently live in?",

    "occupation":
        "What is your current occupation?",

    "employment_status":
        "What is your current employment status?",

    "student":
        "Are you currently a student?",

    "education_level":
        "What is your current education level?",

    "class_12_percentile":
        "What is your Class 12 percentile?",

    "course_mode":
        "Are you studying in regular, distance, or correspondence mode?",

    "course_type":
        "What type of course are you pursuing?",

    "institution_recognition":
        "Is your educational institution recognised by the relevant authority?",

    "family_income_annual":
        "What is your annual family income?",

    "annual_income":
        "What is your annual income?",

    "annual_household_income":
        "What is your annual household income?",

    "caste_category":
        "What is your caste category?",

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
        "How much agricultural land do you own or cultivate?",

    "tenant_farmer":
        "Are you a tenant farmer?",

    "landless":
        "Are you landless?",

    "family_land_status":
        "What is your family's agricultural land ownership/status?",

    "cultivable_land_recorded_in_state_ut_land_records":
        "Is your cultivable land recorded in the relevant State/UT land records?",

    "farmer_status":
        "What is your farmer status, such as owner cultivator or tenant farmer?",

    "farmer_type":
        "What type of farmer are you?",

    "farmer_group":
        "Which farmer group or category do you belong to?",

    "borrower_group":
        "Which borrower group applies to you?",

    "allied_activity_status":
        "Do you have an allied agricultural activity such as dairy, poultry, or fisheries?",

    "allied_borrower_group":
        "If you have an allied agricultural activity, which borrower group applies to you?",

    "grows_notified_crop_in_notified_area":
        "Do you grow a notified crop in a notified area?",

    "has_insurable_interest_in_notified_crop":
        "Do you have an insurable interest in the notified crop?",

    "ration_card":
        "Do you have a ration card?",

    "owns_house":
        "Do you already own a house?",

    "has_pucca_house_anywhere_in_india":
        "Do you already own a pucca house anywhere in India?",

    "urban_household":
        "Is your household located in an urban area?",

    "government_employee":
        "Are you or a relevant household member a government employee?",

    "income_tax_payer":
        "Are you an income-tax payer?",

    "marital_status":
        "What is your marital status?",

    "has_children":
        "Do you have children?",

    "children_count":
        "How many children do you have?",

    "other_scholarship_benefit":
        "Are you currently receiving another scholarship or similar educational benefit?",
}


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_field(
    field: Any,
) -> str:

    if field is None:
        return ""

    return str(field).strip()


# ============================================================
# QUESTION GENERATOR
# ============================================================

def generate_questions(
    evaluation: Dict[str, Any],
    max_questions: int = 3,
) -> List[str]:

    if not evaluation:
        return []

    missing_fields = (
        evaluation.get("missing_fields")
        or []
    )

    questions = []

    for field in missing_fields:

        field = _normalize_field(field)

        if not field:
            continue

        question = FIELD_QUESTIONS.get(
            field
        )

        if question is None:
            question = (
                "Please provide information about "
                f"{field.replace('_', ' ')}."
            )

        if question not in questions:
            questions.append(question)

        if len(questions) >= max_questions:
            break

    return questions