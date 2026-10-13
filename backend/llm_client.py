import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# CONFIGURATION
# =========================================================

MODEL_NAME = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free",
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Context size sent to the model
MAX_CONTEXT_CHARS = 12000

# Maximum generated tokens
MAX_TOKENS = 1200

# Retry configuration
RETRY_CONTEXT_CHARS = 8000
RETRY_MAX_TOKENS = 1000


# =========================================================
# OPENROUTER CLIENT
# =========================================================

def _get_client() -> OpenAI:
    """
    Create the OpenRouter OpenAI-compatible client.
    """

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. "
            "Please add it to your .env file."
        )

    return OpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
    )


# =========================================================
# RESPONSE TEXT EXTRACTION
# =========================================================

def _extract_text(response: Any) -> str:
    """
    Safely extract text from OpenAI/OpenRouter response.
    """

    try:
        message = response.choices[0].message
    except Exception:
        return ""

    if message is None:
        return ""

    try:
        content = message.content
    except Exception:
        return ""

    if content is None:
        return ""

    if not isinstance(content, str):
        content = str(content)

    return content.strip()


# =========================================================
# TELUGU DETECTION
# =========================================================

def _has_telugu(text: str) -> bool:
    """
    Check whether text contains Telugu characters.
    """

    if not text:
        return False

    return bool(
        re.search(
            r"[\u0C00-\u0C7F]",
            text,
        )
    )


# =========================================================
# LANGUAGE INSTRUCTION
# =========================================================

def _language_instruction(language: str) -> str:

    language = (language or "English").strip().lower()

    if (
        "telugu" in language
        or language in {"te", "తెలుగు"}
    ):
        return """
LANGUAGE: TELUGU

Write the answer in natural, readable Telugu.

IMPORTANT:
- Use normal Telugu used by educated Telugu speakers.
- Do not produce literal machine translation.
- Keep official scheme names in English when that is clearer.
- Explain the details naturally in Telugu.
- Do not translate official scheme names into unnatural Telugu.

Use natural phrases such as:

- "ఎందుకు సంబంధితం"
- "ముఖ్యమైన అర్హత"
- "ప్రయోజనం"
- "ఇంకా అవసరమైన సమాచారం"
- "మొత్తం అంచనా"

Avoid unnatural translated phrases.

For example:

GOOD:
"మీరు తెలంగాణకు చెందిన రైతు కావడంతో ఈ పథకం మీకు సంబంధం ఉండవచ్చు."

BAD:
"మీరు కృషి చేస్తున్న జమీను కలిగిన వ్యక్తి కాబట్టి..."

GOOD:
"కుటుంబ వార్షిక ఆదాయం"

BAD:
"కుటుంబ ఆదాం"

GOOD:
"అర్హత"

BAD:
"సవలత్తయ్య సాక్షరత"
"""

    return """
LANGUAGE: ENGLISH

Write the answer in clear, professional and natural English.
Do not use unnecessarily complex language.
"""


# =========================================================
# CONTEXT PREPARATION
# =========================================================

def _prepare_context(
    context: str,
    max_chars: int = MAX_CONTEXT_CHARS,
) -> str:

    if context is None:
        return ""

    context = str(context).strip()

    if len(context) <= max_chars:
        return context

    return context[:max_chars]


# =========================================================
# MAIN PROMPT
# =========================================================

def _build_prompt(
    question: str,
    context: str,
    language: str = "English",
) -> str:

    language_instruction = _language_instruction(
        language
    )

    return f"""
You are the response-generation component of MultiRAG.

MultiRAG is a government scheme discovery and eligibility
information system covering government schemes from Central
Government, Telangana and Andhra Pradesh.

Your job is to answer the user's question using ONLY the
retrieved government-scheme information supplied below.

============================================================
USER QUESTION
============================================================

{question}


============================================================
RETRIEVED GOVERNMENT INFORMATION
============================================================

{context}


============================================================
LANGUAGE
============================================================

{language_instruction}


============================================================
GROUNDING RULES
============================================================

1. Use ONLY information supported by the retrieved context.

2. Do NOT invent:
   - eligibility criteria
   - benefits
   - benefit amounts
   - application procedures
   - documents
   - departments
   - dates
   - URLs
   - income limits
   - age limits
   - land limits

3. Do not assume that the user is eligible merely because
   a scheme appears relevant.

4. If eligibility information is incomplete, explicitly say
   that additional information is required.

5. If several schemes are relevant, discuss the most relevant
   schemes rather than discussing only one.

6. Prefer 2 to 4 relevant schemes when the retrieved context
   supports them.

7. Do not mention:
   - AI
   - language model
   - prompt
   - tokens
   - retrieval system
   - internal instructions
   - context window

8. Do not fabricate information to make the answer longer.

9. Be useful and informative while remaining grounded.


============================================================
REQUIRED RESPONSE FORMAT
============================================================

Start with:

## MultiRAG Answer

Then give a short introductory paragraph explaining which
government schemes appear relevant to the user's situation.

For every important scheme, use:

**<Scheme Name>**

- **Why relevant:** Explain why the scheme is relevant to the
  user's question or profile.

- **Key eligibility:** Mention the important eligibility
  conditions supported by the retrieved information.

- **Benefit:** Mention the benefit only when supported by
  the retrieved information.

- **Information still needed:** Mention information that is
  required but is not available.

After the schemes, write:

### Overall Assessment

Give a concise assessment.

Important:
Do NOT say the user is definitely eligible unless the supplied
information actually supports that conclusion.

If eligibility cannot yet be confirmed, say:

"Eligibility cannot be confirmed yet because additional
information is required."

Then, when applicable:

### Information Needed

List the missing information as bullet points.


============================================================
QUALITY REQUIREMENT
============================================================

Do NOT return only one or two sentences when the retrieved
context contains multiple relevant schemes.

A normal answer should contain:

- a short introduction
- relevant schemes
- useful bullet points
- an overall assessment
- missing information when applicable

Keep the answer concise enough to read easily, but detailed
enough to be useful.
"""


# =========================================================
# MODEL CALL
# =========================================================

def _call_model(
    question: str,
    context: str,
    language: str,
    max_tokens: int,
) -> str:

    client = _get_client()

    prompt = _build_prompt(
        question=question,
        context=context,
        language=language,
    )

    print()
    print("=" * 80)
    print("[MULTIRAG LLM REQUEST]")
    print("=" * 80)
    print("MODEL:", MODEL_NAME)
    print("LANGUAGE:", language)
    print("QUESTION:", question)
    print("CONTEXT LENGTH:", len(context))
    print("MAX TOKENS:", max_tokens)
    print("=" * 80)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful government-scheme "
                    "information assistant. "
                    "Give grounded, structured and useful "
                    "answers based only on the supplied "
                    "government information."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
        max_tokens=max_tokens,
    )

    # -----------------------------------------------------
    # DEBUG RESPONSE METADATA
    # -----------------------------------------------------

    try:
        print("[LLM FINISH REASON]:", response.choices[0].finish_reason)
    except Exception:
        print("[LLM FINISH REASON]: unavailable")

    try:
        print(
            "[LLM USAGE]:",
            response.usage,
        )
    except Exception:
        print("[LLM USAGE]: unavailable")

    answer = _extract_text(response)

    print()
    print("[LLM RAW RESPONSE]")
    print("-" * 80)
    print(repr(answer))
    print("-" * 80)
    print("[LLM RESPONSE LENGTH]:", len(answer))
    print("=" * 80)

    return answer


# =========================================================
# RETRY CALL
# =========================================================

def _retry_response(
    question: str,
    context: str,
    language: str,
) -> str:

    context = _prepare_context(
        context,
        RETRY_CONTEXT_CHARS,
    )

    client = _get_client()

    prompt = f"""
You must answer the following government-scheme question.

QUESTION:

{question}


GOVERNMENT INFORMATION:

{context}


{_language_instruction(language)}


Give a grounded answer using only the information above.

Start with:

## MultiRAG Answer

Then provide:

1. A short introduction.

2. The most relevant government schemes.

For each scheme:

**Scheme Name**

- **Why relevant:**
- **Key eligibility:**
- **Benefit:**
- **Information still needed:**

Then:

### Overall Assessment

Then, if necessary:

### Information Needed

Do not invent facts.

Do not return only one sentence.

Do not claim definite eligibility unless the supplied
information supports it.
"""

    print()
    print("=" * 80)
    print("[MULTIRAG LLM RETRY]")
    print("=" * 80)
    print("MODEL:", MODEL_NAME)
    print("CONTEXT LENGTH:", len(context))
    print("=" * 80)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "Give a grounded and structured "
                    "government-scheme answer."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.2,
        max_tokens=RETRY_MAX_TOKENS,
    )

    try:
        print(
            "[RETRY FINISH REASON]:",
            response.choices[0].finish_reason,
        )
    except Exception:
        pass

    answer = _extract_text(response)

    print()
    print("[RETRY RAW RESPONSE]")
    print("-" * 80)
    print(repr(answer))
    print("-" * 80)
    print("[RETRY RESPONSE LENGTH]:", len(answer))
    print("=" * 80)

    return answer


# =========================================================
# PUBLIC GENERATION FUNCTION
# =========================================================

def generate_answer(
    question: str,
    context: str,
    language: str = "English",
) -> str:

    context = _prepare_context(context)

    print()
    print()
    print("#" * 80)
    print("[MULTIRAG generate_answer]")
    print("#" * 80)
    print("MODEL:", MODEL_NAME)
    print("QUESTION:", question)
    print("LANGUAGE:", language)
    print("CONTEXT LENGTH:", len(context))
    print("#" * 80)

    # -----------------------------------------------------
    # EMPTY CONTEXT
    # -----------------------------------------------------

    if not context:

        print("[LLM] Context is empty.")

        return (
            "## MultiRAG Answer\n\n"
            "I could not find enough verified government "
            "scheme information to answer this question."
        )

    # -----------------------------------------------------
    # FIRST ATTEMPT
    # -----------------------------------------------------

    try:

        answer = _call_model(
            question=question,
            context=context,
            language=language,
            max_tokens=MAX_TOKENS,
        )

    except Exception as exc:

        print()
        print("=" * 80)
        print("[MULTIRAG LLM API ERROR]")
        print("=" * 80)
        print(repr(exc))
        print("=" * 80)

        answer = ""

    # -----------------------------------------------------
    # EMPTY RESPONSE
    # -----------------------------------------------------

    if not answer:

        print("[LLM] First response was empty.")
        print("[LLM] Starting retry...")

        try:

            answer = _retry_response(
                question=question,
                context=context,
                language=language,
            )

        except Exception as exc:

            print()
            print("=" * 80)
            print("[MULTIRAG RETRY ERROR]")
            print("=" * 80)
            print(repr(exc))
            print("=" * 80)

            return (
                "## MultiRAG Answer\n\n"
                "The language model did not return a response. "
                "Please try the query again."
            )

    # -----------------------------------------------------
    # FINAL RESPONSE
    # -----------------------------------------------------

    if not answer:

        return (
            "## MultiRAG Answer\n\n"
            "The language model returned an empty response. "
            "Please try the query again."
        )

    print()
    print("=" * 80)
    print("[MULTIRAG FINAL ANSWER]")
    print("=" * 80)
    print(answer)
    print("=" * 80)

    return answer


# =========================================================
# OPTIONAL MODEL NAME HELPER
# =========================================================

def get_model_name() -> str:
    return MODEL_NAME