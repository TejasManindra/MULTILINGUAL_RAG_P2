import re
import streamlit as st

from backend.data_loader import (
    load_rag_documents,
    build_scheme_index,
)

from backend.scheme_search import hybrid_search
from backend.eligibility_service import check_eligibility
from backend.llm_client import generate_answer


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
# LOAD DATA
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
# LANGUAGE
# ============================================================

def detect_language(text: str) -> str:
    """
    Detect the user's preferred response language.

    Telugu characters -> Telugu
    Otherwise -> English
    """

    if not text:
        return "english"

    telugu_chars = sum(
        1
        for char in text
        if "\u0C00" <= char <= "\u0C7F"
    )

    english_chars = sum(
        1
        for char in text
        if char.isascii() and char.isalpha()
    )

    if telugu_chars == 0:
        return "english"

    if english_chars == 0:
        return "telugu"

    # Mixed Telugu + English:
    # Telugu is preferred for the final answer.
    if telugu_chars >= english_chars * 0.25:
        return "telugu"

    return "english"


# ============================================================
# LANGUAGE INSTRUCTION
# ============================================================

def get_language_instruction(
    response_language: str,
) -> str:

    if response_language == "telugu":

        return """
LANGUAGE REQUIREMENT:
Respond entirely in Telugu.

Important rules:
- Explain the answer naturally in Telugu.
- Keep official scheme names in their original form when useful.
- Keep official URLs unchanged.
- Government department names may remain in English if that
  preserves official terminology.
- Do not invent facts.
- Do not infer missing eligibility information.
- Do not convert percentage marks into percentile.
- Clearly state when more information is required.
- Clearly distinguish between confirmed eligibility and
  possible relevance.
"""

    return """
LANGUAGE REQUIREMENT:
Respond entirely in English.

Important rules:
- Keep official scheme names in their original form.
- Keep official URLs unchanged.
- Do not invent facts.
- Do not infer missing eligibility information.
- Do not convert percentage marks into percentile.
- Clearly state when more information is required.
- Clearly distinguish between confirmed eligibility and
  possible relevance.
"""


# ============================================================
# SAFE VALUE
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


# ============================================================
# SCHEME NAME
# ============================================================

def get_scheme_name(
    scheme: dict,
) -> str:

    return (
        scheme.get("scheme_name")
        or scheme.get("official_scheme_name")
        or "Government Scheme"
    )


# ============================================================
# FORMAT RULES
# ============================================================

def format_rules(rules) -> str:

    if not rules:
        return "No structured rules available."

    if isinstance(rules, str):
        return rules

    if not isinstance(rules, list):
        return str(rules)

    output = []

    for rule in rules:

        if isinstance(rule, dict):

            description = (
                rule.get("description")
                or rule.get("condition")
                or rule.get("rule")
                or rule.get("field")
                or str(rule)
            )

            output.append(
                f"- {description}"
            )

        else:

            output.append(
                f"- {rule}"
            )

    return "\n".join(output)


# ============================================================
# ELIGIBILITY CONTEXT
# ============================================================

def build_eligibility_context(
    eligibility_result: dict,
) -> str:
    """
    Build strictly grounded context from the deterministic
    eligibility service.

    The LLM is only responsible for explaining the result.
    It does NOT decide eligibility.
    """

    if not eligibility_result:
        return (
            "NO ELIGIBILITY RESULT AVAILABLE.\n"
            "Do not invent information."
        )

    query = eligibility_result.get(
        "query",
        "",
    )

    profile = eligibility_result.get(
        "profile",
        {},
    )

    overall_status = eligibility_result.get(
        "overall_status",
        "NO_RELEVANT_SCHEME",
    )

    response_language = eligibility_result.get(
        "response_language",
        "english",
    )

    next_questions = eligibility_result.get(
        "next_questions",
        [],
    )

    results = eligibility_result.get(
        "results",
        [],
    )

    context_parts = []

    context_parts.append(
        f"""
============================================================
MULTIRAG ELIGIBILITY RESULT
============================================================

USER QUERY
----------
{query}

RESPONSE LANGUAGE
-----------------
{response_language}

OVERALL STATUS
--------------
{overall_status}

USER PROFILE
------------
{profile}

IMPORTANT:
The eligibility status above was produced by the deterministic
rule-based eligibility engine.

The LLM must NOT change, override, or reinterpret the status.

============================================================
"""
    )

    for index, scheme in enumerate(
        results,
        start=1,
    ):

        if not isinstance(scheme, dict):
            continue

        scheme_name = get_scheme_name(
            scheme
        )

        status = scheme.get(
            "status",
            "UNKNOWN",
        )

        government_level = safe_value(
            scheme.get(
                "government_level"
            )
        )

        state = safe_value(
            scheme.get("state")
        )

        category = safe_value(
            scheme.get("category")
        )

        target = safe_value(
            scheme.get(
                "target_beneficiary"
            )
        )

        benefit = safe_value(
            scheme.get(
                "benefit_description"
            )
        )

        scheme_status = safe_value(
            scheme.get(
                "scheme_status"
            )
        )

        verification_status = safe_value(
            scheme.get(
                "verification_status"
            )
        )

        eligibility_rules = format_rules(
            scheme.get(
                "eligibility_rules",
                [],
            )
        )

        exclusion_rules = format_rules(
            scheme.get(
                "exclusion_rules",
                [],
            )
        )

        missing_fields = scheme.get(
            "missing_fields",
            [],
        )

        failed_rules = scheme.get(
            "failed_rules",
            [],
        )

        unsupported_rules = scheme.get(
            "unsupported_rules",
            [],
        )

        questions = scheme.get(
            "questions",
            [],
        )

        source_url = safe_value(
            scheme.get(
                "source_url"
            ),
            "Not available",
        )

        source_file = safe_value(
            scheme.get(
                "source_file"
            ),
            "Not available",
        )

        document_title = safe_value(
            scheme.get(
                "document_title"
            ),
            "Not available",
        )

        evaluation = scheme.get(
            "evaluation"
        ) or {}

        reason = evaluation.get(
            "reason"
        )

        context_parts.append(
            f"""
============================================================
SCHEME {index}
============================================================

SCHEME NAME
-----------
{scheme_name}

STATUS
------
{status}

GOVERNMENT LEVEL
----------------
{government_level}

STATE
-----
{state}

CATEGORY
--------
{category}

TARGET BENEFICIARY
------------------
{target}

SCHEME STATUS
-------------
{scheme_status}

VERIFICATION STATUS
-------------------
{verification_status}

BENEFIT
-------
{benefit}

ELIGIBILITY RULES
-----------------
{eligibility_rules}

EXCLUSION RULES
---------------
{exclusion_rules}

MISSING INFORMATION
-------------------
{missing_fields}

FAILED RULES
------------
{failed_rules}

UNSUPPORTED RULES
-----------------
{unsupported_rules}

FOLLOW-UP QUESTIONS
-------------------
{questions}

EVALUATION REASON
-----------------
{reason or "Not specified"}

OFFICIAL SOURCE
---------------
{source_url}

SOURCE FILE
-----------
{source_file}

DOCUMENT TITLE
--------------
{document_title}

============================================================
"""
        )

    if next_questions:

        context_parts.append(
            """
============================================================
NEXT QUESTIONS
============================================================
"""
        )

        for index, question in enumerate(
            next_questions,
            start=1,
        ):

            if isinstance(question, dict):

                question_text = question.get(
                    "question",
                    str(question),
                )

            else:

                question_text = str(
                    question
                )

            context_parts.append(
                f"{index}. {question_text}\n"
            )

    return "\n".join(
        context_parts
    )


# ============================================================
# GENERAL SEARCH CONTEXT
# ============================================================

def build_search_context(
    results,
) -> str:
    """
    Context for normal Scheme Search.

    Uses hybrid_search results directly.
    """

    if not results:

        return (
            "NO RELEVANT GOVERNMENT INFORMATION "
            "WAS RETRIEVED.\n"
            "Do not invent information."
        )

    context_parts = []

    seen = set()

    for index, result in enumerate(
        results,
        start=1,
    ):

        if not isinstance(result, dict):
            continue

        scheme_name = (
            result.get("scheme_name")
            or "Government Scheme"
        )

        if scheme_name in seen:
            continue

        seen.add(
            scheme_name
        )

        context_parts.append(
            f"""
============================================================
GOVERNMENT SOURCE {index}
============================================================

Scheme Name:
{scheme_name}

Government Level:
{safe_value(result.get("government_level"))}

State:
{safe_value(result.get("state"))}

Category:
{safe_value(result.get("category"))}

Subcategory:
{safe_value(result.get("subcategory"))}

Target Beneficiary:
{safe_value(result.get("target_beneficiary"))}

Scheme Status:
{safe_value(result.get("scheme_status"))}

Benefit:
{safe_value(result.get("benefit_description"))}

Eligibility Rules:
{format_rules(result.get("eligibility_rules"))}

Exclusion Rules:
{format_rules(result.get("exclusion_rules"))}

Official Source:
{safe_value(
    result.get("source_url"),
    "Not available",
)}

Source File:
{safe_value(
    result.get("source_file"),
    "Not available",
)}

Document Title:
{safe_value(
    result.get("document_title"),
    "Not available",
)}

Evidence Text:
{safe_value(
    result.get("text"),
    "Not available",
)}

============================================================
"""
        )

    return "\n".join(
        context_parts
    )


# ============================================================
# GENERAL HYBRID SEARCH
# ============================================================

def run_hybrid_search(
    query: str,
    region: str,
    limit: int = 8,
):

    try:

        detected_scheme, detected_state, results = (
            hybrid_search(
                query=query.strip(),
                top_k=max(limit, 8),
            )
        )

    except Exception as error:

        st.error(
            f"Search failed: {error}"
        )

        return (
            None,
            None,
            [],
        )

    # --------------------------------------------------------
    # Region filter
    # --------------------------------------------------------

    filtered = []

    for result in results:

        if not isinstance(result, dict):
            continue

        result_state = (
            str(
                result.get(
                    "state",
                    "",
                )
            )
            .strip()
            .lower()
        )

        government_level = (
            str(
                result.get(
                    "government_level",
                    "",
                )
            )
            .strip()
            .lower()
        )

        if region == "All Regions":
            filtered.append(result)

        elif region == "Central Government":

            if (
                government_level
                == "central"
            ):
                filtered.append(result)

        elif region == "Telangana":

            if (
                government_level == "central"
                or result_state == "telangana"
            ):
                filtered.append(result)

        elif region == "Andhra Pradesh":

            if (
                government_level == "central"
                or result_state
                in {
                    "andhra pradesh",
                    "andhra_pradesh",
                }
            ):
                filtered.append(result)

    # Deduplicate scheme names.

    final_results = []

    seen = set()

    for result in filtered:

        scheme_name = (
            result.get("scheme_name")
            or result.get("scheme_id")
        )

        if scheme_name in seen:
            continue

        seen.add(
            scheme_name
        )

        final_results.append(
            result
        )

        if len(final_results) >= limit:
            break

    return (
        detected_scheme,
        detected_state,
        final_results,
    )


# ============================================================
# GENERAL LLM RESPONSE
# ============================================================

def generate_general_answer(
    query: str,
    results,
    response_language: str,
):

    context = build_search_context(
        results
    )

    language_instruction = (
        get_language_instruction(
            response_language
        )
    )

    prompt = f"""
{language_instruction}

You are MultiRAG, a grounded government scheme
information assistant.

Answer the user's question ONLY using the supplied
government information.

USER QUESTION
-------------
{query}

GOVERNMENT INFORMATION
----------------------
{context}

STRICT RULES
------------
1. Do not invent eligibility requirements.
2. Do not invent benefits.
3. Do not invent application procedures.
4. Do not treat semantic similarity as eligibility.
5. Do not convert marks into percentile.
6. If information is missing, say that it is missing.
7. Preserve official scheme names.
8. Preserve official URLs.
9. Clearly distinguish verified information from
   information that requires confirmation.
10. If the user asks for eligibility, do not make
    the final eligibility decision yourself. The
    deterministic eligibility engine is responsible
    for that.
"""

    try:

        answer = generate_answer(
            question=query,
            context=prompt,
            language=(
                "Telugu"
                if response_language == "telugu"
                else "English"
            ),
        )

        return answer

    except Exception as error:

        return (
            "Unable to generate the AI response.\n\n"
            f"Technical error: {error}"
        )


# ============================================================
# ELIGIBILITY LLM RESPONSE
# ============================================================

def generate_eligibility_answer(
    query: str,
    eligibility_result: dict,
) -> str:

    response_language = eligibility_result.get(
        "response_language",
        detect_language(query),
    )

    language_instruction = (
        get_language_instruction(
            response_language
        )
    )

    context = build_eligibility_context(
        eligibility_result
    )

    prompt = f"""
{language_instruction}

You are the response-generation layer of MultiRAG.

The deterministic eligibility engine has already
evaluated the government scheme rules.

Your job is ONLY to explain those results clearly
to the user.

USER QUESTION
-------------
{query}

DETERMINISTIC ELIGIBILITY RESULT
---------------------------------
{context}

STRICT RESPONSE RULES
---------------------

1. Do NOT change the eligibility status.

2. Do NOT independently decide that the user is eligible
   or ineligible.

3. If status is NEED_MORE_INFORMATION, clearly say that
   more information is required.

4. If status is ELIGIBLE, explain that the deterministic
   rules currently available indicate eligibility, but
   final approval is by the concerned authority.

5. If status is NOT_ELIGIBLE, explain which documented
   rule failed.

6. If status is RULES_REQUIRE_REVIEW, explain that the
   available information is insufficient to safely
   confirm current eligibility.

7. Never invent missing income limits.

8. Never say that an income is "within the limit" unless
   the supplied government evidence explicitly provides
   the applicable limit and the deterministic engine
   supports that comparison.

9. NEVER convert percentage marks into percentile.

   Example:
   "85% marks" does NOT automatically mean
   "85th percentile".

10. If a scheme requires a percentile and the user only
    supplied percentage marks, explain that the percentile
    is still unknown.

11. Do not claim that the user qualifies for a scheme
    merely because they are a student or resident.

12. Do not claim "typical limits", "usually eligible",
    or similar unsupported assumptions.

13. Keep official scheme names and URLs unchanged.

14. Keep the response concise and easy to understand.

15. Use headings and bullet points.

16. If next questions are supplied, show them under
    a "Next information needed" section.

17. End with a short statement that final approval is
    determined by the concerned government authority.

"""

    try:

        answer = generate_answer(
            question=query,
            context=prompt,
            language=(
                "Telugu"
                if response_language == "telugu"
                else "English"
            ),
        )

        return answer

    except Exception as error:

        if response_language == "telugu":

            return (
                "AI సమాధానం రూపొందించడంలో సమస్య ఏర్పడింది.\n\n"
                f"Technical error: {error}"
            )

        return (
            "Unable to generate the AI response.\n\n"
            f"Technical error: {error}"
        )


# ============================================================
# SOURCE DISPLAY FOR ELIGIBILITY
# ============================================================

def display_eligibility_sources(
    eligibility_result: dict,
):

    results = eligibility_result.get(
        "results",
        [],
    )

    if not results:
        return

    st.divider()

    response_language = (
        eligibility_result.get(
            "response_language",
            "english",
        )
    )

    if response_language == "telugu":

        st.subheader(
            "సంబంధిత ప్రభుత్వ పథకాలు"
        )

    else:

        st.subheader(
            "Relevant Government Schemes"
        )

    for scheme in results:

        scheme_name = get_scheme_name(
            scheme
        )

        status = scheme.get(
            "status",
            "UNKNOWN",
        )

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {scheme_name}"
            )

            col1, col2, col3 = st.columns(
                3
            )

            with col1:

                st.caption(
                    "Government Level"
                )

                st.write(
                    safe_value(
                        scheme.get(
                            "government_level"
                        )
                    )
                )

            with col2:

                st.caption(
                    "State"
                )

                st.write(
                    safe_value(
                        scheme.get(
                            "state"
                        )
                    )
                )

            with col3:

                st.caption(
                    "Eligibility Status"
                )

                if status == "ELIGIBLE":

                    st.success(status)

                elif status == "NEED_MORE_INFORMATION":

                    st.warning(status)

                elif status == "NOT_ELIGIBLE":

                    st.error(status)

                else:

                    st.info(status)

            benefit = scheme.get(
                "benefit_description"
            )

            if benefit:

                if response_language == "telugu":

                    st.write(
                        f"**ప్రయోజనం:** {benefit}"
                    )

                else:

                    st.write(
                        f"**Benefit:** {benefit}"
                    )

            source_url = scheme.get(
                "source_url"
            )

            if source_url:

                st.link_button(
                    "Official Source",
                    source_url,
                )

            missing_fields = scheme.get(
                "missing_fields",
                [],
            )

            if missing_fields:

                if response_language == "telugu":

                    st.caption(
                        "ఇంకా అవసరమైన సమాచారం: "
                        + ", ".join(
                            missing_fields
                        )
                    )

                else:

                    st.caption(
                        "Missing information: "
                        + ", ".join(
                            missing_fields
                        )
                    )


# ============================================================
# GENERAL SOURCE DISPLAY
# ============================================================

def display_general_sources(
    results,
):

    if not results:
        return

    st.divider()

    st.subheader(
        "Retrieved Government Sources"
    )

    seen = set()

    for result in results:

        scheme_name = (
            result.get("scheme_name")
            or "Government Scheme"
        )

        if scheme_name in seen:
            continue

        seen.add(
            scheme_name
        )

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {scheme_name}"
            )

            government_level = safe_value(
                result.get(
                    "government_level"
                )
            )

            state = safe_value(
                result.get("state")
            )

            category = safe_value(
                result.get("category")
            )

            st.caption(
                f"{government_level} · "
                f"{state} · "
                f"{category}"
            )

            target = result.get(
                "target_beneficiary"
            )

            if target:

                st.write(
                    f"**Target beneficiary:** {target}"
                )

            status = result.get(
                "scheme_status"
            )

            if status:

                st.caption(
                    f"Status: {status}"
                )

            benefit = result.get(
                "benefit_description"
            )

            if benefit:

                st.write(
                    f"**Benefit:** {benefit}"
                )

            source_url = result.get(
                "source_url"
            )

            if source_url:

                st.link_button(
                    "Official Source",
                    source_url,
                )


# ============================================================
# CLEAN ANSWER
# ============================================================

def clean_llm_output(
    text: str,
) -> str:

    if not text:
        return ""

    # Remove accidental Streamlit anchor artifacts.
    text = re.sub(
        r"\[svg\]\(http://localhost:8501/#[^)]+\)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


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

    ui_language = st.selectbox(
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

    st.divider()

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

    st.caption(
        f"RAG Documents: {len(RAG_DOCUMENTS)}"
    )

    st.caption(
        f"Indexed Schemes: {len(SCHEME_INDEX)}"
    )

    st.divider()

    st.caption(
        "MultiRAG P2"
    )

    st.caption(
        "Multilingual Government Scheme Intelligence"
    )


# ============================================================
# PAGE
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

    if ui_language == "తెలుగు":

        st.title(
            "ప్రభుత్వ పథకాలను కనుగొనండి"
        )

        st.write(
            "మీ అవసరాన్ని తెలుగులో లేదా ఇంగ్లీష్‌లో "
            "తెలియజేయండి. MultiRAG సంబంధిత ప్రభుత్వ "
            "సమాచారాన్ని శోధించి సమాధానం ఇస్తుంది."
        )

        placeholder = (
            "ఉదా: నేను తెలంగాణ రైతును. "
            "నాకు ఏ ప్రభుత్వ పథకాలు అందుబాటులో ఉన్నాయి?"
        )

        button_text = (
            "సంబంధిత పథకాలను కనుగొనండి →"
        )

    else:

        st.title(
            "Find Government Schemes"
        )

        st.write(
            "Ask your question in English or Telugu. "
            "MultiRAG retrieves relevant government "
            "information and provides a grounded answer."
        )

        placeholder = (
            "Example: I am a farmer from Telangana. "
            "What schemes can I get?"
        )

        button_text = (
            "Find Relevant Schemes →"
        )

    query = st.text_area(
        "Search Government Schemes",
        placeholder=placeholder,
        height=120,
        key="dashboard_query",
    )

    if st.button(
        button_text,
        type="primary",
        use_container_width=True,
        key="dashboard_search",
    ):

        if not query.strip():

            if ui_language == "తెలుగు":

                st.warning(
                    "దయచేసి మీ అవసరాన్ని నమోదు చేయండి."
                )

            else:

                st.warning(
                    "Please enter your requirement."
                )

        else:

            response_language = detect_language(
                query
            )

            with st.spinner(
                "Searching government information..."
            ):

                eligibility_result = (
                    check_eligibility(
                        query,
                        max_schemes=6,
                    )
                )

                # ------------------------------------------------
                # Eligibility query
                # ------------------------------------------------

                if eligibility_result.get(
                    "intent"
                ) == "ELIGIBILITY":

                    answer = (
                        generate_eligibility_answer(
                            query,
                            eligibility_result,
                        )
                    )

                    answer = clean_llm_output(
                        answer
                    )

                    st.markdown(
                        "## MultiRAG Answer"
                    )

                    st.markdown(
                        answer,
                        unsafe_allow_html=False,
                    )

                    display_eligibility_sources(
                        eligibility_result
                    )

                # ------------------------------------------------
                # Discovery / information query
                # ------------------------------------------------

                else:

                    (
                        detected_scheme,
                        detected_state,
                        results,
                    ) = run_hybrid_search(
                        query=query,
                        region=region,
                        limit=8,
                    )

                    answer = (
                        generate_general_answer(
                            query=query,
                            results=results,
                            response_language=response_language,
                        )
                    )

                    answer = clean_llm_output(
                        answer
                    )

                    st.markdown(
                        "## MultiRAG Answer"
                    )

                    st.markdown(
                        answer,
                        unsafe_allow_html=False,
                    )

                    display_general_sources(
                        results
                    )


# ============================================================
# SCHEME SEARCH
# ============================================================

elif page == "Scheme Search":

    if ui_language == "తెలుగు":

        st.title(
            "పథకం శోధన"
        )

        st.write(
            "ప్రభుత్వ పథకం గురించి మీ ప్రశ్నను నమోదు చేయండి."
        )

        placeholder = (
            "ఉదా: తెలంగాణలో రైతులకు ఏ పథకాలు ఉన్నాయి?"
        )

        search_button = "శోధించండి →"

    else:

        st.title(
            "Scheme Search"
        )

        st.write(
            "Search the government scheme knowledge base."
        )

        placeholder = (
            "Example: What schemes are available "
            "for farmers in Telangana?"
        )

        search_button = "Search →"

    query = st.text_area(
        "Query",
        placeholder=placeholder,
        height=120,
    )

    if st.button(
        search_button,
        type="primary",
        use_container_width=True,
    ):

        if not query.strip():

            st.warning(
                "Please enter a query."
            )

        else:

            response_language = detect_language(
                query
            )

            with st.spinner(
                "Searching..."
            ):

                (
                    detected_scheme,
                    detected_state,
                    results,
                ) = run_hybrid_search(
                    query=query,
                    region=region,
                    limit=10,
                )

            if not results:

                if response_language == "telugu":

                    st.warning(
                        "సంబంధిత ప్రభుత్వ సమాచారం "
                        "కనుగొనబడలేదు."
                    )

                else:

                    st.warning(
                        "No relevant government information found."
                    )

            else:

                answer = generate_general_answer(
                    query=query,
                    results=results,
                    response_language=response_language,
                )

                st.markdown(
                    "## MultiRAG Answer"
                )

                st.markdown(
                    clean_llm_output(answer),
                    unsafe_allow_html=False,
                )

                display_general_sources(
                    results
                )


# ============================================================
# ELIGIBILITY CHECK
# ============================================================

elif page == "Eligibility Check":

    if ui_language == "తెలుగు":

        st.title(
            "అర్హత తనిఖీ"
        )

        st.write(
            "మీ వయస్సు, రాష్ట్రం, ఆదాయం, విద్య, "
            "వృత్తి వంటి వివరాలను సహజ భాషలో నమోదు చేయండి."
        )

        placeholder = (
            "ఉదా: నేను తెలంగాణకు చెందిన విద్యార్థిని. "
            "నాకు 12వ తరగతిలో 85% మార్కులు వచ్చాయి. "
            "మా కుటుంబ ఆదాయం 3 లక్షలు. "
            "నేను రెగ్యులర్ డిగ్రీ చదువుతున్నాను. "
            "నాకు స్కాలర్‌షిప్ వస్తుందా?"
        )

        button_text = (
            "నా అర్హతను తనిఖీ చేయండి →"
        )

    else:

        st.title(
            "Eligibility Check"
        )

        st.write(
            "Describe your situation in natural language. "
            "The system extracts your profile and evaluates "
            "documented scheme rules deterministically."
        )

        placeholder = (
            "Example: I am a student from Telangana. "
            "I got 85% in 12th, my family income is "
            "3 lakhs and I am studying a regular degree. "
            "Can I get a scholarship?"
        )

        button_text = (
            "Check My Eligibility →"
        )

    query = st.text_area(
        "Your Details",
        placeholder=placeholder,
        height=180,
        key="eligibility_query",
    )

    if st.button(
        button_text,
        type="primary",
        use_container_width=True,
        key="eligibility_button",
    ):

        if not query.strip():

            if ui_language == "తెలుగు":

                st.warning(
                    "దయచేసి మీ వివరాలను నమోదు చేయండి."
                )

            else:

                st.warning(
                    "Please enter your details."
                )

        else:

            with st.spinner(
                "Evaluating documented government rules..."
            ):

                eligibility_result = (
                    check_eligibility(
                        query,
                        max_schemes=8,
                    )
                )

            response_language = (
                eligibility_result.get(
                    "response_language",
                    detect_language(query),
                )
            )

            # Debug information can be useful during development.
            with st.expander(
                "System Details"
            ):

                st.write(
                    "Detected language:",
                    response_language,
                )

                st.write(
                    "Intent:",
                    eligibility_result.get(
                        "intent"
                    ),
                )

                st.write(
                    "Detected state:",
                    eligibility_result.get(
                        "detected_state"
                    ),
                )

                st.write(
                    "Detected scheme:",
                    eligibility_result.get(
                        "detected_scheme"
                    ),
                )

                st.write(
                    "Profile:",
                    eligibility_result.get(
                        "profile"
                    ),
                )

                st.write(
                    "Overall status:",
                    eligibility_result.get(
                        "overall_status"
                    ),
                )

            answer = generate_eligibility_answer(
                query,
                eligibility_result,
            )

            answer = clean_llm_output(
                answer
            )

            st.markdown(
                "## MultiRAG Answer"
            )

            st.markdown(
                answer,
                unsafe_allow_html=False,
            )

            display_eligibility_sources(
                eligibility_result
            )

            # ----------------------------------------------------
            # Next questions
            # ----------------------------------------------------

            next_questions = (
                eligibility_result.get(
                    "next_questions",
                    [],
                )
            )

            if next_questions:

                if response_language == "telugu":

                    st.subheader(
                        "తదుపరి అవసరమైన సమాచారం"
                    )

                else:

                    st.subheader(
                        "Next Information Needed"
                    )

                for index, question in enumerate(
                    next_questions,
                    start=1,
                ):

                    if isinstance(
                        question,
                        dict,
                    ):

                        question_text = question.get(
                            "question",
                            str(question),
                        )

                    else:

                        question_text = str(
                            question
                        )

                    st.write(
                        f"{index}. {question_text}"
                    )


# ============================================================
# SCHEME CATALOGUE
# ============================================================

elif page == "Scheme Catalogue":

    if ui_language == "తెలుగు":

        st.title(
            "పథకాల క్యాటలాగ్"
        )

    else:

        st.title(
            "Scheme Catalogue"
        )

    # Build unique schemes from loaded RAG data.

    catalogue = {}

    for document in RAG_DOCUMENTS:

        if not isinstance(
            document,
            dict,
        ):
            continue

        scheme_id = (
            document.get("scheme_id")
            or document.get("scheme_name")
        )

        if not scheme_id:
            continue

        if scheme_id not in catalogue:

            catalogue[scheme_id] = document

    catalogue_items = list(
        catalogue.values()
    )

    st.caption(
        f"{len(catalogue_items)} unique schemes"
    )

    search_text = st.text_input(
        "Filter schemes",
        placeholder="Search by scheme name, state or category...",
    )

    filtered_catalogue = []

    normalized_search = (
        search_text.strip().lower()
        if search_text
        else ""
    )

    for scheme in catalogue_items:

        if not normalized_search:

            filtered_catalogue.append(
                scheme
            )

            continue

        searchable = " ".join(
            str(
                scheme.get(
                    field,
                    "",
                )
            )
            for field in [
                "scheme_name",
                "category",
                "subcategory",
                "state",
                "target_beneficiary",
            ]
        ).lower()

        if normalized_search in searchable:

            filtered_catalogue.append(
                scheme
            )

    for scheme in filtered_catalogue:

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {get_scheme_name(scheme)}"
            )

            st.caption(
                f"{safe_value(scheme.get('government_level'))} "
                f"· {safe_value(scheme.get('state'))} "
                f"· {safe_value(scheme.get('category'))}"
            )

            target = scheme.get(
                "target_beneficiary"
            )

            if target:

                st.write(
                    f"**Target:** {target}"
                )

            benefit = scheme.get(
                "benefit_description"
            )

            if benefit:

                st.write(
                    f"**Benefit:** {benefit}"
                )

            status = scheme.get(
                "scheme_status"
            )

            if status:

                st.caption(
                    f"Status: {status}"
                )


# ============================================================
# GOVERNMENT SOURCES
# ============================================================

elif page == "Government Sources":

    if ui_language == "తెలుగు":

        st.title(
            "ప్రభుత్వ మూలాలు"
        )

        st.write(
            "MultiRAG ఉపయోగిస్తున్న ప్రభుత్వ పథకాల "
            "మూల సమాచారాన్ని ఇక్కడ చూడవచ్చు."
        )

    else:

        st.title(
            "Government Sources"
        )

        st.write(
            "Government source information available "
            "in the MultiRAG knowledge base."
        )

    seen = set()

    for document in RAG_DOCUMENTS:

        if not isinstance(
            document,
            dict,
        ):
            continue

        scheme_name = get_scheme_name(
            document
        )

        if scheme_name in seen:
            continue

        seen.add(
            scheme_name
        )

        source_url = document.get(
            "source_url"
        )

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {scheme_name}"
            )

            st.caption(
                f"{safe_value(document.get('government_level'))} "
                f"· {safe_value(document.get('state'))}"
            )

            if source_url:

                st.link_button(
                    "Official Source",
                    source_url,
                )


# ============================================================
# RECENT UPDATES
# ============================================================

elif page == "Recent Updates":

    if ui_language == "తెలుగు":

        st.title(
            "ఇటీవలి సమాచారం"
        )

        st.info(
            "ప్రస్తుతం ప్రాజెక్ట్‌లోని ప్రభుత్వ "
            "మూలాల ఆధారంగా సమాచారం ప్రదర్శించబడుతోంది."
        )

    else:

        st.title(
            "Recent Updates"
        )

        st.info(
            "Information shown here is based on the "
            "government sources currently available "
            "in the MultiRAG knowledge base."
        )

    # Show currently indexed documents as a simple
    # knowledge-base snapshot.

    st.metric(
        "Indexed Government Records",
        len(RAG_DOCUMENTS),
    )

    st.metric(
        "Unique Scheme Metadata",
        len(SCHEME_INDEX),
    )