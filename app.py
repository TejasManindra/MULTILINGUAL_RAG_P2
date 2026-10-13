import re

import streamlit as st

from backend.data_loader import (
    load_rag_documents,
    build_scheme_index,
)

from backend.llm_client import generate_answer
from backend.scheme_search import hybrid_search
from backend.eligibility_service import check_eligibility


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="MultiRAG | Government Scheme Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# LOAD BACKEND DATA
# ============================================================

@st.cache_data
def get_rag_documents():
    try:
        return load_rag_documents()
    except Exception as error:
        st.error(
            f"Unable to load RAG documents: {error}"
        )
        return []


@st.cache_data
def get_scheme_index():
    try:
        return build_scheme_index()
    except Exception as error:
        st.error(
            f"Unable to load scheme metadata: {error}"
        )
        return {}


RAG_DOCUMENTS = get_rag_documents()
SCHEME_INDEX = get_scheme_index()


# ============================================================
# DATASET VALUES
# ============================================================

def get_unique_scheme_count(documents):
    """
    Count unique schemes from the actual RAG dataset.

    Uses scheme_id when available and falls back to
    scheme_name.
    """

    unique_schemes = set()

    for document in documents:

        if not isinstance(document, dict):
            continue

        scheme_id = document.get("scheme_id")
        scheme_name = document.get("scheme_name")

        key = scheme_id or scheme_name

        if key:
            unique_schemes.add(
                str(key).strip()
            )

    return len(unique_schemes)


INDEXED_SCHEME_COUNT = get_unique_scheme_count(
    RAG_DOCUMENTS
)


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_value(
    value,
    default="Not specified",
):
    if value is None:
        return default

    if isinstance(value, str):

        value = value.strip()

        if not value:
            return default

    return value


def get_scheme_name(result):

    if not isinstance(result, dict):
        return "Government Scheme"

    if result.get("scheme_name"):
        return result.get("scheme_name")

    scheme = result.get("scheme") or {}
    document = result.get("document") or {}

    return (
        scheme.get("official_scheme_name")
        or scheme.get("scheme_name")
        or document.get("scheme_name")
        or "Government Scheme"
    )


def get_scheme_field(
    result,
    field,
    default=None,
):

    if not isinstance(result, dict):
        return default

    if (
        field in result
        and result.get(field) is not None
    ):
        return result.get(field)

    scheme = result.get("scheme") or {}
    document = result.get("document") or {}

    value = scheme.get(field)

    if value is not None:
        return value

    value = document.get(field)

    if value is not None:
        return value

    return default


def get_source_url(result):

    if not isinstance(result, dict):
        return None

    source_url = result.get("source_url")

    if source_url:
        return source_url

    source = result.get("source") or {}

    return source.get("source_url")


def get_document_text(result):

    if not isinstance(result, dict):
        return ""

    chunks = result.get("chunks") or []

    if chunks:

        texts = []

        for chunk in chunks:

            if isinstance(chunk, dict):

                text = chunk.get("text")

                if text:
                    texts.append(
                        str(text)
                    )

        if texts:
            return "\n\n".join(texts)

    document = result.get("document") or {}

    return document.get("text") or ""


def get_page_number(result):

    if not isinstance(result, dict):
        return None

    chunks = result.get("chunks") or []

    for chunk in chunks:

        if isinstance(chunk, dict):

            page = chunk.get("page_number")

            if page is not None:
                return page

    document = result.get("document") or {}

    return document.get("page_number")


def get_rules(result):

    if not isinstance(result, dict):
        return []

    rules = result.get(
        "eligibility_rules"
    )

    if rules:
        return rules

    nested_rules = result.get(
        "rules"
    ) or {}

    return (
        nested_rules.get(
            "eligibility_rules"
        )
        or []
    )


def get_exclusion_rules(result):

    if not isinstance(result, dict):
        return []

    rules = result.get(
        "exclusion_rules"
    )

    if rules:
        return rules

    nested_rules = result.get(
        "rules"
    ) or {}

    return (
        nested_rules.get(
            "exclusion_rules"
        )
        or []
    )


def format_rule_list(rules):

    if not rules:
        return "No structured rules available."

    if not isinstance(
        rules,
        list,
    ):
        return str(rules)

    formatted = []

    for rule in rules:

        if isinstance(rule, dict):

            description = (
                rule.get("description")
                or rule.get("condition")
                or rule.get("rule")
                or rule.get("question")
                or rule.get("field")
                or str(rule)
            )

        else:

            description = str(rule)

        formatted.append(
            f"- {description}"
        )

    return "\n".join(formatted)


# ============================================================
# REGION FILTERING
# ============================================================

def normalize_region(region):

    value = str(
        region or ""
    ).strip().lower()

    mapping = {
        "all regions": "all",
        "central government": "central",
        "telangana": "telangana",
        "andhra pradesh": "andhra pradesh",
    }

    return mapping.get(
        value,
        value,
    )


def region_matches(
    result,
    region,
):

    region = normalize_region(
        region
    )

    if region == "all":
        return True

    government_level = str(
        get_scheme_field(
            result,
            "government_level",
            "",
        )
        or ""
    ).strip().lower()

    state = str(
        get_scheme_field(
            result,
            "state",
            "",
        )
        or ""
    ).strip().lower()

    if region == "central":

        return (
            government_level
            == "central"
        )

    if region == "telangana":

        return (
            government_level
            == "telangana"
            or state
            == "telangana"
            or "telangana"
            in government_level
        )

    if region == "andhra pradesh":

        return (
            government_level
            == "andhra pradesh"
            or state
            == "andhra pradesh"
            or "andhra"
            in government_level
        )

    return True


def category_matches(
    result,
    category,
):

    if (
        not category
        or category
        == "All Categories"
    ):
        return True

    requested = str(
        category
    ).strip().lower()

    actual_category = str(
        get_scheme_field(
            result,
            "category",
            "",
        )
        or ""
    ).strip().lower()

    actual_subcategory = str(
        get_scheme_field(
            result,
            "subcategory",
            "",
        )
        or ""
    ).strip().lower()

    combined = (
        f"{actual_category} "
        f"{actual_subcategory}"
    )

    aliases = {

        "education": [
            "education",
            "scholarship",
            "student",
        ],

        "agriculture": [
            "agriculture",
            "farmer",
            "farming",
            "crop",
            "kisan",
        ],

        "health": [
            "health",
            "medical",
            "healthcare",
            "insurance",
        ],

        "housing": [
            "housing",
            "house",
            "home",
            "shelter",
        ],

        "entrepreneurship": [
            "entrepreneur",
            "enterprise",
            "msme",
            "business",
            "self employment",
            "livelihood",
        ],

        "social welfare": [
            "social",
            "pension",
            "welfare",
            "financial assistance",
        ],

        "women welfare": [
            "women",
            "woman",
            "girl",
            "female",
            "women welfare",
        ],
    }

    keywords = aliases.get(
        requested,
        [requested],
    )

    return any(
        keyword in combined
        for keyword in keywords
    )


# ============================================================
# RETRIEVAL
# ============================================================

def retrieve_schemes(
    query,
    region,
    category="All Categories",
    limit=6,
):

    if (
        not query
        or not query.strip()
    ):
        return []

    if not RAG_DOCUMENTS:
        return []

    try:

        (
            detected_scheme,
            detected_state,
            results,
        ) = hybrid_search(
            query=query.strip(),
            top_k=max(
                limit,
                8,
            ),
        )

        if not results:
            return []

        filtered_results = []

        for result in results:

            if not isinstance(
                result,
                dict,
            ):
                continue

            if not region_matches(
                result,
                region,
            ):
                continue

            if not category_matches(
                result,
                category,
            ):
                continue

            filtered_results.append(
                result
            )

            if len(
                filtered_results
            ) >= limit:
                break

        return filtered_results

    except Exception as error:

        st.error(
            f"Retrieval failed: {error}"
        )

        return []


# ============================================================
# AI CONTEXT
# ============================================================

def build_ai_context(results):

    if not results:

        return (
            "NO RELEVANT GOVERNMENT "
            "INFORMATION WAS RETRIEVED.\n\n"
            "Do not invent information."
        )

    context_parts = []

    seen_schemes = set()

    for number, result in enumerate(
        results,
        start=1,
    ):

        if not isinstance(
            result,
            dict,
        ):
            continue

        scheme_name = get_scheme_name(
            result
        )

        if scheme_name in seen_schemes:
            continue

        seen_schemes.add(
            scheme_name
        )

        government_level = safe_value(
            get_scheme_field(
                result,
                "government_level",
            )
        )

        state = safe_value(
            get_scheme_field(
                result,
                "state",
            )
        )

        category = safe_value(
            get_scheme_field(
                result,
                "category",
            )
        )

        subcategory = safe_value(
            get_scheme_field(
                result,
                "subcategory",
            )
        )

        target_beneficiary = safe_value(
            get_scheme_field(
                result,
                "target_beneficiary",
            )
        )

        scheme_status = safe_value(
            get_scheme_field(
                result,
                "scheme_status",
            )
        )

        benefit_description = safe_value(
            get_scheme_field(
                result,
                "benefit_description",
            )
        )

        source_url = safe_value(
            get_source_url(result),
            "Not available",
        )

        source_status = safe_value(
            get_scheme_field(
                result,
                "source_status",
            )
        )

        verification_status = safe_value(
            get_scheme_field(
                result,
                "verification_status",
            )
        )

        eligibility_rules = get_rules(
            result
        )

        exclusion_rules = (
            get_exclusion_rules(
                result
            )
        )

        eligibility_text = (
            format_rule_list(
                eligibility_rules
            )
        )

        exclusion_text = (
            format_rule_list(
                exclusion_rules
            )
        )

        page = get_page_number(
            result
        )

        retrieved_text = safe_value(
            get_document_text(result),
            "No retrieved document text available.",
        )

        context = f"""
============================================================
GOVERNMENT SOURCE {number}
============================================================

SCHEME INFORMATION
------------------
Scheme Name:
{scheme_name}

Government Level:
{government_level}

State:
{state}

Category:
{category}

Subcategory:
{subcategory}

Target Beneficiary:
{target_beneficiary}

Scheme Status:
{scheme_status}

Verification Status:
{verification_status}

BENEFITS
--------
{benefit_description}

STRUCTURED ELIGIBILITY RULES
----------------------------
{eligibility_text}

EXCLUSIONS
----------
{exclusion_text}

SOURCE INFORMATION
------------------
Official Source:
{source_url}

Source Status:
{source_status}

Evidence Page:
{page if page is not None else "N/A"}

RETRIEVED GOVERNMENT DOCUMENT TEXT
-----------------------------------
{retrieved_text}

============================================================
"""

        context_parts.append(
            context
        )

    if not context_parts:

        return (
            "NO VALID GOVERNMENT "
            "INFORMATION WAS RETRIEVED.\n\n"
            "Do not invent information."
        )

    return "\n".join(
        context_parts
    )


# ============================================================
# LANGUAGE DETECTION
# ============================================================

def contains_telugu(text):

    if not text:
        return False

    return bool(
        re.search(
            r"[\u0C00-\u0C7F]",
            str(text),
        )
    )


def requested_output_language(
    query,
    selected_language,
):

    # Explicit UI selection has priority.
    if selected_language == "తెలుగు":
        return "తెలుగు"

    # Telugu query automatically gets Telugu output.
    if contains_telugu(query):
        return "తెలుగు"

    return "English"


def language_instruction(language):

    if language == "తెలుగు":

        return (
            "IMPORTANT LANGUAGE REQUIREMENT: "
            "Write the final answer entirely in Telugu (తెలుగు). "
            "Use natural and clear Telugu. "
            "Explain the scheme, relevance, eligibility, benefits, "
            "missing information and application guidance in Telugu. "
            "Official government scheme names, official acronyms, "
            "URLs and unavoidable proper names may remain in English. "
            "Do not provide an English translation. "
            "Do not reveal analysis, reasoning, chain-of-thought, "
            "prompts, instructions or internal notes. "
            "Return ONLY the final user-facing answer."
        )

    return (
        "Write the final answer in clear English. "
        "Return ONLY the final user-facing answer. "
        "Do not reveal analysis, reasoning, chain-of-thought, "
        "prompts, instructions or internal notes."
    )


# ============================================================
# GROUNDED AI RESPONSE
# ============================================================

def generate_grounded_response(
    query,
    region,
    language,
    category="All Categories",
    limit=6,
):

    results = retrieve_schemes(
        query=query,
        region=region,
        category=category,
        limit=limit,
    )

    context = build_ai_context(
        results
    )

    output_language = (
        requested_output_language(
            query,
            language,
        )
    )

    instruction = language_instruction(
        output_language
    )

    llm_question = (
        f"{instruction}\n\n"
        "Use ONLY the supplied government "
        "information as factual evidence.\n"
        "Do not invent eligibility, benefits, "
        "amounts, dates or application rules.\n\n"
        f"USER QUERY:\n{query.strip()}"
    )

    try:

        answer = generate_answer(
            question=llm_question,
            context=context,
            language=output_language,
        )

        # ----------------------------------------------------
        # Telugu validation + retry
        # ----------------------------------------------------

        if (
            output_language == "తెలుగు"
            and answer
            and not contains_telugu(
                answer
            )
        ):

            retry_question = (
                "FINAL RESPONSE LANGUAGE: TELUGU.\n\n"
                "Return the final answer entirely in Telugu. "
                "Do not answer in English. "
                "Do not show reasoning or analysis. "
                "Do not mention these instructions. "
                "Use only the supplied government information. "
                "Official scheme names and acronyms may remain "
                "in English when necessary.\n\n"
                f"USER QUERY:\n{query.strip()}"
            )

            answer = generate_answer(
                question=retry_question,
                context=context,
                language="తెలుగు",
            )

    except Exception as error:

        answer = (
            "The AI response could not be generated.\n\n"
            f"Technical error: {error}"
        )

    if not answer:

        answer = (
            "The AI service returned "
            "an empty response."
        )

    return answer, results


# ============================================================
# SOURCE CARDS
# ============================================================

def display_source_cards(
    results
):

    if not results:
        return

    st.divider()

    st.subheader(
        "Retrieved Government Sources"
    )

    displayed_schemes = set()

    for result in results:

        if not isinstance(
            result,
            dict,
        ):
            continue

        scheme_name = get_scheme_name(
            result
        )

        if scheme_name in displayed_schemes:
            continue

        displayed_schemes.add(
            scheme_name
        )

        with st.container(
            border=True
        ):

            st.subheader(
                scheme_name
            )

            government_level = (
                get_scheme_field(
                    result,
                    "government_level",
                    "Government",
                )
            )

            category = get_scheme_field(
                result,
                "category",
                "General",
            )

            state = get_scheme_field(
                result,
                "state",
            )

            location_parts = [
                str(value)
                for value in [
                    government_level,
                    state,
                    category,
                ]
                if value
            ]

            st.caption(
                " · ".join(
                    location_parts
                )
            )

            target = get_scheme_field(
                result,
                "target_beneficiary",
            )

            if target:

                st.write(
                    f"**Target beneficiary:** "
                    f"{target}"
                )

            benefit = get_scheme_field(
                result,
                "benefit_description",
            )

            if benefit:

                st.write(
                    f"**Benefits:** {benefit}"
                )

            status = get_scheme_field(
                result,
                "scheme_status",
            )

            if status:

                st.caption(
                    f"Status: {status}"
                )

            page = get_page_number(
                result
            )

            if page is not None:

                st.caption(
                    f"Evidence page: {page}"
                )

            source_url = get_source_url(
                result
            )

            if source_url:

                st.link_button(
                    "Official Source",
                    source_url,
                )


# ============================================================
# CLEAN AI OUTPUT
# ============================================================

def clean_llm_output(text):

    if not text:
        return ""

    text = str(text).strip()

    # Remove common localhost citation artifacts.
    text = re.sub(
        r"\[sv\]\(http://localhost:8501/#[^)]+\)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove common leaked analysis headers.
    leaked_headers = [
        r"^here'?s a thinking process:\s*",
        r"^thinking process:\s*",
        r"^analysis:\s*",
        r"^chain of thought:\s*",
    ]

    for pattern in leaked_headers:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        )

    return text.strip()


def show_ai_answer(
    answer,
    results,
):

    st.markdown(
        "## MultiRAG Answer"
    )

    clean_answer = clean_llm_output(
        answer
    )

    if clean_answer:

        st.markdown(
            clean_answer,
            unsafe_allow_html=False,
        )

    else:

        st.error(
            "The AI service returned "
            "an empty answer."
        )

    if results:

        display_source_cards(
            results
        )

    else:

        st.warning(
            "No relevant government "
            "information was retrieved."
        )

    st.info(
        "This response is based on the currently "
        "connected government information. Final "
        "eligibility, approval and benefits are "
        "determined by the concerned government authority."
    )


# ============================================================
# ELIGIBILITY HELPERS
# ============================================================

def eligibility_status_badge(
    status
):

    status = str(
        status or "UNKNOWN"
    ).upper()

    if status == "ELIGIBLE":

        st.success(
            "✓ Eligible based on the available rules"
        )

    elif status == "NOT_ELIGIBLE":

        st.error(
            "✕ Not eligible based on the available rules"
        )

    elif status == "NEED_MORE_INFORMATION":

        st.warning(
            "⚠ More information is required"
        )

    elif status == "RULES_REQUIRE_REVIEW":

        st.info(
            "ℹ Rules require manual review"
        )

    elif status == "UNSUPPORTED":

        st.info(
            "ℹ This rule could not be evaluated automatically"
        )

    elif status == "SCHEMES_FOUND":

        st.success(
            "✓ Relevant schemes found"
        )

    else:

        st.info(
            str(status)
            .replace(
                "_",
                " ",
            )
            .title()
        )


def display_rule_description(
    rule
):

    if isinstance(
        rule,
        dict,
    ):

        return (
            rule.get("description")
            or rule.get("condition")
            or rule.get("rule")
            or rule.get("question")
            or rule.get("field")
            or str(rule)
        )

    return str(rule)


def display_eligibility_scheme(
    result,
    index,
):

    if not isinstance(
        result,
        dict,
    ):
        return

    scheme_name = safe_value(
        result.get("scheme_name"),
        "Government Scheme",
    )

    status = result.get(
        "status",
        "UNKNOWN",
    )

    with st.container(
        border=True
    ):

        title_col, status_col = st.columns(
            [5, 2]
        )

        with title_col:

            st.subheader(
                f"{index}. {scheme_name}"
            )

            geography = []

            if result.get(
                "government_level"
            ):

                geography.append(
                    str(
                        result.get(
                            "government_level"
                        )
                    )
                )

            if result.get("state"):

                geography.append(
                    str(
                        result.get(
                            "state"
                        )
                    )
                )

            if geography:

                st.caption(
                    " · ".join(
                        geography
                    )
                )

        with status_col:

            eligibility_status_badge(
                status
            )

        # ----------------------------------------------------
        # Scheme information
        # ----------------------------------------------------

        info_col1, info_col2 = st.columns(
            2
        )

        with info_col1:

            category = result.get(
                "category"
            )

            if category:

                st.write(
                    f"**Category:** {category}"
                )

            target = result.get(
                "target_beneficiary"
            )

            if target:

                st.write(
                    f"**Target beneficiary:** "
                    f"{target}"
                )

        with info_col2:

            scheme_status = result.get(
                "scheme_status"
            )

            if scheme_status:

                st.write(
                    f"**Scheme status:** "
                    f"{scheme_status}"
                )

            relevance = result.get(
                "eligibility_relevance"
            )

            if relevance is not None:

                try:

                    st.write(
                        f"**Relevance:** "
                        f"{float(relevance):.2f}"
                    )

                except Exception:

                    st.write(
                        f"**Relevance:** "
                        f"{relevance}"
                    )

        # ----------------------------------------------------
        # Benefit
        # ----------------------------------------------------

        benefit = result.get(
            "benefit_description"
        )

        if benefit:

            st.markdown(
                f"**Benefit:** {benefit}"
            )

        # ----------------------------------------------------
        # Evaluation
        # ----------------------------------------------------

        st.markdown(
            "#### Eligibility Assessment"
        )

        evaluation = (
            result.get(
                "evaluation"
            )
            or {}
        )

        missing_fields = (
            result.get(
                "missing_fields",
                [],
            )
            or []
        )

        failed_rules = (
            result.get(
                "failed_rules",
                [],
            )
            or []
        )

        unsupported_rules = (
            result.get(
                "unsupported_rules",
                [],
            )
            or []
        )

        matched_rules = (
            evaluation.get(
                "matched_rules",
                [],
            )
            or evaluation.get(
                "passed_rules",
                [],
            )
            or []
        )

        count1, count2, count3, count4 = (
            st.columns(4)
        )

        with count1:

            st.metric(
                "Passed",
                len(
                    matched_rules
                ),
            )

        with count2:

            st.metric(
                "Failed",
                len(
                    failed_rules
                ),
            )

        with count3:

            st.metric(
                "Missing",
                len(
                    missing_fields
                ),
            )

        with count4:

            st.metric(
                "Unsupported",
                len(
                    unsupported_rules
                ),
            )

        # ----------------------------------------------------
        # Missing information
        # ----------------------------------------------------

        if missing_fields:

            st.markdown(
                "#### Missing Information"
            )

            for field in missing_fields:

                readable_field = (
                    str(field)
                    .replace(
                        "_",
                        " ",
                    )
                    .title()
                )

                st.warning(
                    readable_field
                )

        # ----------------------------------------------------
        # Questions
        # ----------------------------------------------------

        questions = (
            result.get(
                "questions",
                [],
            )
            or []
        )

        if questions:

            st.markdown(
                "#### Additional Questions"
            )

            for question in questions:

                if isinstance(
                    question,
                    dict,
                ):

                    question_text = (
                        question.get(
                            "question"
                        )
                        or str(question)
                    )

                else:

                    question_text = str(
                        question
                    )

                st.write(
                    f"• {question_text}"
                )

        # ----------------------------------------------------
        # Failed rules
        # ----------------------------------------------------

        if failed_rules:

            st.markdown(
                "#### Conditions Not Satisfied"
            )

            for rule in failed_rules:

                st.error(
                    display_rule_description(
                        rule
                    )
                )

        # ----------------------------------------------------
        # Unsupported rules
        # ----------------------------------------------------

        if unsupported_rules:

            st.markdown(
                "#### Rules Requiring Review"
            )

            for rule in unsupported_rules:

                st.info(
                    display_rule_description(
                        rule
                    )
                )

        # ----------------------------------------------------
        # Passed rules
        # ----------------------------------------------------

        if matched_rules:

            with st.expander(
                "View passed conditions"
            ):

                for rule in matched_rules:

                    st.success(
                        display_rule_description(
                            rule
                        )
                    )

        # ----------------------------------------------------
        # Eligibility rules
        # ----------------------------------------------------

        eligibility_rules = result.get(
            "eligibility_rules"
        )

        if eligibility_rules:

            with st.expander(
                "View scheme eligibility rules"
            ):

                if isinstance(
                    eligibility_rules,
                    list,
                ):

                    for rule in eligibility_rules:

                        st.write(
                            "• "
                            + display_rule_description(
                                rule
                            )
                        )

                else:

                    st.write(
                        eligibility_rules
                    )

        # ----------------------------------------------------
        # Historical / proposed warning
        # ----------------------------------------------------

        if result.get(
            "historical_or_proposed"
        ):

            st.warning(
                "This scheme is marked as historical "
                "or proposed in the knowledge base. "
                "Its current availability requires "
                "verification from the official source."
            )

        # ----------------------------------------------------
        # Current status warning
        # ----------------------------------------------------

        if (
            result.get(
                "current_status_confirmed"
            )
            is False
        ):

            st.warning(
                "The current status or current-cycle "
                "availability could not be fully confirmed "
                "from the knowledge base."
            )

        # ----------------------------------------------------
        # Source
        # ----------------------------------------------------

        source_url = result.get(
            "source_url"
        )

        if source_url:

            st.link_button(
                "View Official Source",
                source_url,
            )


def display_eligibility_response(
    response
):

    if not response:

        st.error(
            "No eligibility response was returned."
        )

        return

    overall_status = response.get(
        "status",
        response.get(
            "overall_status",
            "UNKNOWN",
        ),
    )

    st.markdown(
        "## Eligibility Result"
    )

    eligibility_status_badge(
        overall_status
    )

    router = response.get(
        "router",
        {},
    ) or {}

    if router:

        with st.expander(
            "Query interpretation",
            expanded=False,
        ):

            intent = router.get(
                "intent"
            )

            detected_scheme = router.get(
                "detected_scheme"
            )

            detected_state = router.get(
                "detected_state"
            )

            if intent:

                st.write(
                    f"**Intent:** {intent}"
                )

            if detected_scheme:

                st.write(
                    f"**Detected scheme:** "
                    f"{detected_scheme}"
                )

            if detected_state:

                st.write(
                    f"**Detected state:** "
                    f"{detected_state}"
                )

    profile = response.get(
        "profile",
        {},
    ) or {}

    if profile:

        with st.expander(
            "Extracted profile",
            expanded=False,
        ):

            for key, value in profile.items():

                if value is None:
                    continue

                readable_key = (
                    str(key)
                    .replace(
                        "_",
                        " ",
                    )
                    .title()
                )

                st.write(
                    f"**{readable_key}:** "
                    f"{value}"
                )

    topics = response.get(
        "topics",
        [],
    ) or []

    if topics:

        st.write(
            "**Detected topics:** "
            + ", ".join(
                str(topic)
                for topic in topics
            )
        )

    next_questions = response.get(
        "next_questions",
        [],
    ) or []

    if next_questions:

        st.subheader(
            "Information Needed"
        )

        for question in next_questions:

            if isinstance(
                question,
                dict,
            ):

                question_text = (
                    question.get(
                        "question"
                    )
                    or question.get(
                        "text"
                    )
                    or str(question)
                )

            else:

                question_text = str(
                    question
                )

            st.info(
                question_text
            )

    results = response.get(
        "results",
        [],
    ) or response.get(
        "schemes",
        [],
    ) or []

    if results:

        st.subheader(
            "Scheme Assessments"
        )

        for index, result in enumerate(
            results,
            start=1,
        ):

            display_eligibility_scheme(
                result,
                index,
            )

    message = response.get(
        "message"
    )

    if message:

        st.info(
            message
        )

    st.caption(
        "Final eligibility, approval and benefits "
        "are determined by the concerned government authority."
    )


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       GLOBAL THEME
       ======================================================== */

    .stApp {
        background: #0F172A;
        color: #E2E8F0;
    }

    .main .block-container {
        max-width: 1400px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }


    /* ========================================================
       HEADINGS
       ======================================================== */

    h1, h2, h3, h4 {
        color: #F1F5F9 !important;
        font-weight: 700 !important;
    }

    h1 {
        letter-spacing: -0.5px;
    }

    h2, h3 {
        letter-spacing: -0.2px;
    }


    /* ========================================================
       NORMAL TEXT
       ======================================================== */

    p {
        color: #CBD5E1;
    }

    .stCaption,
    [data-testid="stCaptionContainer"] {
        color: #94A3B8 !important;
    }


    /* ========================================================
       SIDEBAR
       ======================================================== */

    section[data-testid="stSidebar"] {
        background: #111C30;
        border-right: 1px solid #26354D;
    }

    section[data-testid="stSidebar"] * {
        color: #CBD5E1;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #F1F5F9 !important;
    }


    /* ========================================================
       INPUTS
       ======================================================== */

    input,
    textarea {
        background-color: #1E293B !important;
        color: #F1F5F9 !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }

    input::placeholder,
    textarea::placeholder {
        color: #64748B !important;
        opacity: 1 !important;
    }

    input:focus,
    textarea:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 1px #3B82F6 !important;
    }


    /* ========================================================
       SELECT BOXES
       ======================================================== */

    div[data-baseweb="select"] > div {
        background-color: #1E293B !important;
        color: #F1F5F9 !important;
        border-color: #334155 !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="select"] span {
        color: #F1F5F9 !important;
    }

    div[data-baseweb="select"] svg {
        fill: #94A3B8 !important;
    }


    /* ========================================================
       SELECTBOX / DROPDOWN POPUP
       ======================================================== */

    div[role="listbox"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
    }

    div[role="option"] {
        background-color: #1E293B !important;
        color: #E2E8F0 !important;
    }

    div[role="option"]:hover {
        background-color: #273449 !important;
        color: #FFFFFF !important;
    }


    /* ========================================================
       BUTTONS
       ======================================================== */

    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        min-height: 42px;
        transition: all 0.2s ease;
    }

    /* Primary button */
    .stButton > button[kind="primary"] {
        background: #2563EB !important;
        border: 1px solid #2563EB !important;
        color: #FFFFFF !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: #3B82F6 !important;
        border-color: #3B82F6 !important;
    }

    /* Normal button */
    .stButton > button[kind="secondary"] {
        background: #1E293B !important;
        border: 1px solid #334155 !important;
        color: #E2E8F0 !important;
    }

    .stButton > button[kind="secondary"]:hover {
        background: #273449 !important;
        border-color: #475569 !important;
    }


    /* ========================================================
       CARDS / CONTAINERS
       ======================================================== */

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #162235;
        border: 1px solid #26354D;
        border-radius: 10px;
    }


    /* ========================================================
       METRICS
       ======================================================== */

    div[data-testid="stMetric"] {
        background: #162235;
        border: 1px solid #26354D;
        border-radius: 10px;
        padding: 16px;
    }

    div[data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #F1F5F9 !important;
    }


    /* ========================================================
       EXPANDERS
       ======================================================== */

    div[data-testid="stExpander"] {
        background: #162235;
        border: 1px solid #26354D;
        border-radius: 8px;
    }

    div[data-testid="stExpander"] summary {
        color: #E2E8F0 !important;
    }


    /* ========================================================
       ALERTS
       ======================================================== */

    div[data-testid="stAlert"] {
        border-radius: 8px;
    }


    /* ========================================================
       LINKS
       ======================================================== */

    a {
        color: #60A5FA !important;
    }

    a:hover {
        color: #93C5FD !important;
    }


    /* ========================================================
       DIVIDERS
       ======================================================== */

    hr {
        border-color: #26354D !important;
    }


    /* ========================================================
       SCROLLBAR
       ======================================================== */

    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #0F172A;
    }

    ::-webkit-scrollbar-thumb {
        background: #334155;
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #475569;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title(
        "🏛️ MultiRAG"
    )

    st.caption(
        "Government Scheme Intelligence"
    )

    st.divider()

    st.markdown(
        "### AREA"
    )

    active_area = st.radio(
        "Area",
        [
            "Discover",
            "Knowledge",
        ],
        label_visibility="collapsed",
    )

    st.markdown(
        "### DISCOVER"
    )

    discover_page = st.radio(
        "Discover",
        [
            "Dashboard",
            "Scheme Search",
            "Eligibility Check",
            "Scheme Catalogue",
        ],
        label_visibility="collapsed",
    )

    st.markdown(
        "### KNOWLEDGE"
    )

    knowledge_page = st.radio(
        "Knowledge",
        [
            "Government Sources",
            "Recent Updates",
        ],
        label_visibility="collapsed",
    )

    st.markdown(
        "### PREFERENCES"
    )

    language = st.selectbox(
        "Language",
        [
            "English",
            "తెలుగు",
        ],
    )

    region = st.selectbox(
        "Region",
        [
            "All Regions",
            "Central Government",
            "Telangana",
            "Andhra Pradesh",
        ],
    )

    st.markdown(
        "### SYSTEM STATUS"
    )

    if RAG_DOCUMENTS:

        st.success(
            "● RAG Data Connected"
        )

    else:

        st.error(
            "● RAG Data Not Available"
        )

    if SCHEME_INDEX:

        st.success(
            "● Metadata Connected"
        )

    else:

        st.error(
            "● Metadata Not Available"
        )

    st.caption(
        f"RAG Documents: "
        f"{len(RAG_DOCUMENTS)}"
    )

    st.caption(
        f"Indexed Schemes: "
        f"{INDEXED_SCHEME_COUNT}"
    )

    st.divider()

    st.caption(
        "MultiRAG P2"
    )

    st.caption(
        "v0.6.1"
    )


# ============================================================
# PAGE SELECTION
# ============================================================

if active_area == "Discover":

    page = discover_page

else:

    page = knowledge_page


# ============================================================
# TOP BAR
# ============================================================

top_left, top_right = st.columns(
    [6, 1]
)

with top_left:

    st.caption(
        "MULTILINGUAL GOVERNMENT AI"
    )

with top_right:

    st.success(
        "● Connected"
    )

st.divider()


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    st.title(
        "Find Government Schemes"
    )

    st.header(
        "That Fit You"
    )

    st.write(
        "Ask your question in English or Telugu. "
        "MultiRAG retrieves government information "
        "and generates a grounded response."
    )

    query = st.text_input(
        "Search Government Schemes",
        placeholder=(
            "I am a farmer from Telangana. "
            "What schemes can I apply for?"
        ),
        key="dashboard_query",
    )

    if st.button(
        "Find Relevant Schemes →",
        type="primary",
        use_container_width=True,
        key="dashboard_search",
    ):

        if not query.strip():

            st.warning(
                "Please enter your requirement."
            )

        else:

            with st.spinner(
                "Searching government information "
                "and generating answer..."
            ):

                answer, results = (
                    generate_grounded_response(
                        query=query,
                        region=region,
                        language=language,
                        limit=6,
                    )
                )

            st.session_state[
                "dashboard_answer"
            ] = answer

            st.session_state[
                "dashboard_results"
            ] = results

    if (
        "dashboard_answer"
        in st.session_state
    ):

        show_ai_answer(
            st.session_state[
                "dashboard_answer"
            ],
            st.session_state.get(
                "dashboard_results",
                [],
            ),
        )

    st.caption(
        "Try: Schemes for farmers in Telangana · "
        "Scholarships for students · "
        "Health schemes in Andhra Pradesh"
    )

    st.write("")

    st.subheader(
        "Scheme Intelligence"
    )

    c1, c2, c3, c4 = st.columns(
        4
    )

    with c1:

        st.metric(
            "Indexed Schemes",
            INDEXED_SCHEME_COUNT,
        )

    with c2:

        st.metric(
            "RAG Documents",
            len(RAG_DOCUMENTS),
        )

    with c3:

        st.metric(
            "Target Regions",
            "3",
        )

    with c4:

        st.metric(
            "Languages",
            "2",
        )

    st.write("")

    st.subheader(
        "Explore by Need"
    )

    categories = [
        (
            "🌱",
            "Agriculture",
            "Farmer support and agriculture",
        ),
        (
            "🎓",
            "Education",
            "Scholarships and education",
        ),
        (
            "💼",
            "Employment",
            "Skills and livelihood",
        ),
        (
            "❤️",
            "Health",
            "Healthcare and insurance",
        ),
        (
            "🏠",
            "Housing",
            "Housing assistance",
        ),
        (
            "👥",
            "Women & Child",
            "Women and child welfare",
        ),
        (
            "🏢",
            "MSME",
            "Business and enterprise",
        ),
        (
            "🤝",
            "Social Welfare",
            "Pensions and financial support",
        ),
    ]

    rows = [
        categories[:4],
        categories[4:],
    ]

    for row in rows:

        cols = st.columns(4)

        for col, item in zip(
            cols,
            row,
        ):

            icon, title, description = item

            with col:

                with st.container(
                    border=True
                ):

                    st.markdown(
                        f"### {icon}"
                    )

                    st.write(
                        f"**{title}**"
                    )

                    st.caption(
                        description
                    )

    st.write("")

    st.subheader(
        "How MultiRAG Works"
    )

    steps = [
        (
            "01",
            "Ask",
            "Ask your question in English or Telugu.",
        ),
        (
            "02",
            "Retrieve",
            "Retrieve relevant government information.",
        ),
        (
            "03",
            "Evaluate",
            "Compare information with structured rules.",
        ),
        (
            "04",
            "Guide",
            "Receive grounded guidance with sources.",
        ),
    ]

    cols = st.columns(4)

    for col, step in zip(
        cols,
        steps,
    ):

        number, title, description = step

        with col:

            with st.container(
                border=True
            ):

                st.caption(
                    number
                )

                st.subheader(
                    title
                )

                st.caption(
                    description
                )

    st.info(
        "MultiRAG provides preliminary information. "
        "Final eligibility and approval are determined "
        "by the concerned government authority."
    )


# ============================================================
# SCHEME SEARCH
# ============================================================

elif page == "Scheme Search":

    st.title(
        "Scheme Search"
    )

    st.write(
        "Ask a government scheme question in natural language."
    )

    query = st.text_area(
        "Your Requirement",
        placeholder=(
            "I am a farmer from Telangana "
            "looking for financial support."
        ),
        height=120,
        key="scheme_search_query",
    )

    col1, col2 = st.columns(2)

    with col1:

        category = st.selectbox(
            "Category",
            [
                "All Categories",
                "Agriculture",
                "Education",
                "Health",
                "Housing",
                "Entrepreneurship",
                "Social Welfare",
                "Women Welfare",
            ],
            key="scheme_search_category",
        )

    with col2:

        search_region = st.selectbox(
            "Region",
            [
                "All Regions",
                "Central Government",
                "Telangana",
                "Andhra Pradesh",
            ],
            key="scheme_search_region",
        )

    if st.button(
        "Ask MultiRAG",
        type="primary",
        use_container_width=True,
        key="scheme_search_button",
    ):

        if not query.strip():

            st.warning(
                "Please enter your requirement."
            )

        else:

            with st.spinner(
                "Retrieving government information..."
            ):

                answer, results = (
                    generate_grounded_response(
                        query=query,
                        region=search_region,
                        language=language,
                        category=category,
                        limit=8,
                    )
                )

            st.session_state[
                "search_answer"
            ] = answer

            st.session_state[
                "search_results"
            ] = results

    if (
        "search_answer"
        in st.session_state
    ):

        show_ai_answer(
            st.session_state[
                "search_answer"
            ],
            st.session_state.get(
                "search_results",
                [],
            ),
        )


# ============================================================
# ELIGIBILITY CHECK
# ============================================================

elif page == "Eligibility Check":

    st.title(
        "Eligibility Check"
    )

    st.write(
        "Describe your situation in natural language. "
        "MultiRAG will identify relevant government schemes, "
        "extract your profile and evaluate available rules."
    )

    st.info(
        "The eligibility engine is deterministic and "
        "rule-based. The AI model is not used to make "
        "the final eligibility decision."
    )

    st.subheader(
        "Try an Example"
    )

    example1, example2, example3 = (
        st.columns(3)
    )

    with example1:

        if st.button(
            "🎓 Scholarship",
            use_container_width=True,
            key="eligibility_example_scholarship",
        ):

            st.session_state[
                "eligibility_query"
            ] = (
                "I am a student from Telangana. "
                "I got 85% in 12th and my family income "
                "is 3 lakhs. I am studying a regular "
                "degree course. Can I get a scholarship?"
            )

            st.rerun()

    with example2:

        if st.button(
            "🌱 Agriculture",
            use_container_width=True,
            key="eligibility_example_agriculture",
        ):

            st.session_state[
                "eligibility_query"
            ] = (
                "I am a farmer from Telangana. "
                "What government schemes can I get?"
            )

            st.rerun()

    with example3:

        if st.button(
            "🏠 Housing",
            use_container_width=True,
            key="eligibility_example_housing",
        ):

            st.session_state[
                "eligibility_query"
            ] = (
                "I live in Telangana and I need help "
                "for building a house. Can I get a "
                "housing scheme?"
            )

            st.rerun()

    query = st.text_area(
        "Describe Your Situation",
        placeholder=(
            "Example:\n"
            "I am a student from Telangana. I got 85% "
            "in 12th, my family income is 3 lakhs and "
            "I am studying a regular degree course. "
            "Can I get a scholarship?"
        ),
        height=180,
        key="eligibility_query",
    )

    with st.expander(
        "Advanced Options"
    ):

        max_schemes = st.slider(
            "Maximum schemes to evaluate",
            min_value=1,
            max_value=10,
            value=5,
            step=1,
            key="eligibility_max_schemes",
        )

    if st.button(
        "Check Eligibility →",
        type="primary",
        use_container_width=True,
        key="eligibility_check_button",
    ):

        if not query.strip():

            st.warning(
                "Please describe your situation first."
            )

        else:

            with st.spinner(
                "Understanding your profile, "
                "retrieving schemes and evaluating rules..."
            ):

                try:

                    response = check_eligibility(
                        query=query.strip(),
                        max_schemes=max_schemes,
                    )

                    st.session_state[
                        "eligibility_response"
                    ] = response

                    st.session_state[
                        "eligibility_error"
                    ] = None

                except Exception as error:

                    st.session_state[
                        "eligibility_response"
                    ] = None

                    st.session_state[
                        "eligibility_error"
                    ] = str(error)

    if st.session_state.get(
        "eligibility_error"
    ):

        st.error(
            "Eligibility service error:\n\n"
            + str(
                st.session_state[
                    "eligibility_error"
                ]
            )
        )

    eligibility_response = (
        st.session_state.get(
            "eligibility_response"
        )
    )

    if eligibility_response:

        st.divider()

        display_eligibility_response(
            eligibility_response
        )


# ============================================================
# SCHEME CATALOGUE
# ============================================================

elif page == "Scheme Catalogue":

    st.title(
        "Scheme Catalogue"
    )

    st.write(
        "Browse schemes currently connected "
        "to the MultiRAG knowledge base."
    )

    catalogue_region = st.selectbox(
        "Region",
        [
            "All Regions",
            "Central Government",
            "Telangana",
            "Andhra Pradesh",
        ],
        key="catalogue_region",
    )

    catalogue_items = []

    for scheme_id, metadata in (
        SCHEME_INDEX.items()
    ):

        scheme = metadata.get(
            "scheme",
            {},
        )

        source = metadata.get(
            "source",
            {},
        )

        government_level = str(
            scheme.get(
                "government_level",
                "",
            )
        ).lower()

        if (
            catalogue_region
            == "Central Government"
        ):

            if government_level != "central":
                continue

        elif (
            catalogue_region
            == "Telangana"
        ):

            if government_level not in [
                "telangana",
                "state",
            ]:

                state = str(
                    scheme.get(
                        "state",
                        "",
                    )
                ).lower()

                if state != "telangana":
                    continue

        elif (
            catalogue_region
            == "Andhra Pradesh"
        ):

            if government_level not in [
                "andhra pradesh",
                "state",
            ]:

                state = str(
                    scheme.get(
                        "state",
                        "",
                    )
                ).lower()

                if state != "andhra pradesh":
                    continue

        scheme_name = (
            scheme.get(
                "official_scheme_name"
            )
            or scheme.get(
                "scheme_name"
            )
            or scheme_id
        )

        catalogue_items.append(
            (
                scheme_name,
                scheme,
                source,
            )
        )

    catalogue_items.sort(
        key=lambda item:
        item[0].lower()
    )

    st.write(
        f"**{len(catalogue_items)} "
        f"schemes available**"
    )

    for (
        scheme_name,
        scheme,
        source,
    ) in catalogue_items:

        with st.container(
            border=True
        ):

            st.subheader(
                scheme_name
            )

            st.caption(
                f"{scheme.get('government_level', 'Government')}"
                f" · "
                f"{scheme.get('category', 'General')}"
            )

            target = scheme.get(
                "target_beneficiary"
            )

            if target:

                st.write(
                    f"**Target beneficiary:** "
                    f"{target}"
                )

            benefits = scheme.get(
                "benefit_description"
            )

            if benefits:

                st.write(
                    f"**Benefits:** "
                    f"{benefits}"
                )

            status = scheme.get(
                "scheme_status"
            )

            if status:

                st.caption(
                    f"Status: {status}"
                )

            source_url = source.get(
                "source_url"
            )

            if source_url:

                st.link_button(
                    "Official Source",
                    source_url,
                )


# ============================================================
# GOVERNMENT SOURCES
# ============================================================

elif page == "Government Sources":

    st.title(
        "Government Sources"
    )

    st.write(
        "Official source information associated "
        "with the connected schemes."
    )

    source_items = []

    for scheme_id, metadata in (
        SCHEME_INDEX.items()
    ):

        scheme = metadata.get(
            "scheme",
            {},
        )

        source = metadata.get(
            "source",
            {},
        )

        scheme_name = (
            scheme.get(
                "official_scheme_name"
            )
            or scheme.get(
                "scheme_name"
            )
            or scheme_id
        )

        source_items.append(
            (
                scheme_name,
                scheme,
                source,
            )
        )

    source_items.sort(
        key=lambda item:
        item[0].lower()
    )

    for (
        scheme_name,
        scheme,
        source,
    ) in source_items:

        with st.container(
            border=True
        ):

            st.subheader(
                scheme_name
            )

            col1, col2 = st.columns(2)

            with col1:

                st.write(
                    "**Government Level**"
                )

                st.write(
                    scheme.get(
                        "government_level",
                        "Not specified",
                    )
                )

                st.write(
                    "**Ministry / Department**"
                )

                st.write(
                    scheme.get(
                        "ministry_department",
                        "Not specified",
                    )
                )

            with col2:

                st.write(
                    "**Source Status**"
                )

                st.write(
                    source.get(
                        "source_status",
                        "Not specified",
                    )
                )

                st.write(
                    "**Last Verified**"
                )

                st.write(
                    source.get(
                        "last_verified_date",
                        scheme.get(
                            "last_verified_date",
                            "Not specified",
                        ),
                    )
                )

            source_url = source.get(
                "source_url"
            )

            document_url = source.get(
                "document_url"
            )

            application_url = scheme.get(
                "official_application_url"
            )

            col1, col2, col3 = (
                st.columns(3)
            )

            with col1:

                if source_url:

                    st.link_button(
                        "Official Source Page",
                        source_url,
                    )

            with col2:

                if document_url:

                    st.link_button(
                        "Official Document",
                        document_url,
                    )

            with col3:

                if application_url:

                    st.link_button(
                        "Official Application / Portal",
                        application_url,
                    )


# ============================================================
# RECENT UPDATES
# ============================================================

elif page == "Recent Updates":

    st.title(
        "Recent Updates"
    )

    st.write(
        "Knowledge-base maintenance and source update status."
    )

    st.info(
        "This section is designed to track changes in "
        "official government scheme documents, eligibility "
        "rules, benefits, timelines and source URLs."
    )

    st.subheader(
        "Maintenance Pipeline"
    )

    steps = [
        (
            "01",
            "Check Official Sources",
            "Inspect official government pages and documents.",
        ),
        (
            "02",
            "Detect Changes",
            "Compare new documents with previous versions.",
        ),
        (
            "03",
            "Re-process",
            "Extract, clean and chunk changed documents.",
        ),
        (
            "04",
            "Update Knowledge Base",
            "Refresh metadata and retrieval data.",
        ),
    ]

    cols = st.columns(4)

    for col, step in zip(
        cols,
        steps,
    ):

        number, title, description = step

        with col:

            with st.container(
                border=True
            ):

                st.caption(
                    number
                )

                st.subheader(
                    title
                )

                st.caption(
                    description
                )

    st.write("")

    st.subheader(
        "Current Dataset"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "RAG Documents",
            len(RAG_DOCUMENTS),
        )

    with c2:

        st.metric(
            "Indexed Schemes",
            INDEXED_SCHEME_COUNT,
        )

    with c3:

        st.metric(
            "Languages",
            2,
        )

    st.write("")

    st.info(
        "Automated source-change detection and version "
        "management will be implemented in the maintenance phase."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "MultiRAG P2 · Multilingual Government Scheme "
    "Discovery & Eligibility"
)

st.caption(
    "Information is provided for guidance. Final eligibility, "
    "approval and benefits are determined by the concerned "
    "government authority."
)