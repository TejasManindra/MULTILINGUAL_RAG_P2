import os
import json
from typing import Any, Optional

from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


# ============================================================
# CLIENT
# ============================================================

if OPENROUTER_API_KEY:
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
else:
    client = None


# ============================================================
# MODEL
# ============================================================

# Keep your current model first.
MODEL_NAME = "openrouter/free"


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are MultiRAG, a government scheme information assistant.

Answer the user's question using ONLY the government
information supplied by the application.

IMPORTANT RULES:

1. Do not invent government scheme information.
2. Do not invent eligibility requirements.
3. Do not invent benefits.
4. Do not invent application procedures.
5. Do not invent deadlines.
6. Do not invent URLs.
7. Use only the supplied government information.
8. If the supplied information does not contain the answer,
   clearly say that it is not available.
9. Keep the answer concise and directly answer the question.
10. Do not discuss the internal RAG system.
11. Do not mention retrieval, embeddings, vector databases,
    prompts, models, or internal implementation.

For eligibility questions:

- Do not make a final government eligibility decision.
- Do not convert percentage into percentile.
- Do not invent missing values.
- Clearly separate:
  * information that matches
  * information that is missing
  * information that does not match

Final eligibility and approval are determined by the
concerned government authority.
"""


# ============================================================
# RESPONSE TEXT EXTRACTION
# ============================================================

def _extract_text_from_response(response: Any) -> Optional[str]:
    """
    Safely extract text from an OpenRouter/OpenAI-compatible
    response.

    Different providers may return slightly different
    response structures.
    """

    if response is None:
        return None

    choices = getattr(response, "choices", None)

    if not choices:
        return None

    choice = choices[0]

    # --------------------------------------------------------
    # Standard chat completion
    # --------------------------------------------------------

    message = getattr(choice, "message", None)

    if message is not None:

        content = getattr(message, "content", None)

        if isinstance(content, str) and content.strip():
            return content.strip()

        # Some SDK/provider combinations can return content
        # as a list of content blocks.
        if isinstance(content, list):

            parts = []

            for item in content:

                if isinstance(item, str):
                    parts.append(item)

                elif isinstance(item, dict):

                    text_value = item.get("text")

                    if text_value:
                        parts.append(str(text_value))

                else:

                    text_value = getattr(
                        item,
                        "text",
                        None,
                    )

                    if text_value:
                        parts.append(str(text_value))

            combined = "\n".join(
                part.strip()
                for part in parts
                if part and part.strip()
            )

            if combined:
                return combined

        # Some provider responses may expose reasoning
        # separately. We do NOT use reasoning as the answer
        # unless there is no other response text.
        reasoning = getattr(
            message,
            "reasoning",
            None,
        )

        if isinstance(reasoning, str) and reasoning.strip():
            print(
                "Provider returned reasoning but no message content."
            )

    # --------------------------------------------------------
    # Legacy / alternative text field
    # --------------------------------------------------------

    text_value = getattr(
        choice,
        "text",
        None,
    )

    if isinstance(text_value, str) and text_value.strip():
        return text_value.strip()

    return None


# ============================================================
# RESPONSE DEBUGGING
# ============================================================

def _safe_response_debug(response: Any) -> str:
    """
    Convert an SDK response into readable debug output.
    """

    try:

        if hasattr(response, "model_dump"):

            dumped = response.model_dump()

            return json.dumps(
                dumped,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        if hasattr(response, "model_dump_json"):

            return response.model_dump_json(
                indent=2
            )

    except Exception:
        pass

    try:

        return str(response)

    except Exception:

        return repr(response)


# ============================================================
# GENERATE ANSWER
# ============================================================

def generate_answer(
    question,
    context="",
    language="English",
):

    # --------------------------------------------------------
    # API KEY CHECK
    # --------------------------------------------------------

    if not OPENROUTER_API_KEY:

        return (
            "ERROR: OPENROUTER_API_KEY is not configured.\n\n"
            "Please check your .env file."
        )

    if client is None:

        return (
            "ERROR: OpenRouter client could not be initialized."
        )


    # --------------------------------------------------------
    # CONTEXT CHECK
    # --------------------------------------------------------

    if not context or not str(context).strip():

        context = (
            "NO GOVERNMENT INFORMATION WAS RETRIEVED."
        )

    context = str(context)


    # --------------------------------------------------------
    # LANGUAGE
    # --------------------------------------------------------

    # Support both "Telugu" and "తెలుగు".
    language_normalized = str(
        language or ""
    ).strip().lower()

    if language_normalized in {
        "telugu",
        "తెలుగు",
    }:

        language_instruction = """
Answer primarily in Telugu.

Keep official government scheme names in English
where useful.

Do not translate official scheme names incorrectly.

Use natural, clear Telugu rather than translating
technical field names literally.
"""

    else:

        language_instruction = """
Answer primarily in English.
"""


    # --------------------------------------------------------
    # USER PROMPT
    # --------------------------------------------------------

    user_prompt = f"""
USER QUESTION
=============

{question}


REQUESTED LANGUAGE
==================

{language}

{language_instruction}


GOVERNMENT INFORMATION
======================

{context}


TASK
====

Answer the user's question directly.

Use ONLY the supplied government information.

Do not guess or add information from your own knowledge.

If the question is about one specific scheme, focus on
that scheme instead of listing unrelated schemes.

If the supplied information does not contain the requested
information, say:

"The currently available government information does not
specify this."

For a scheme information question, use this structure
when supported by the supplied information:

Scheme Name:
Why it may be relevant:
Key eligibility:
Main benefit:
Application information:

Only include sections supported by the supplied information.

For eligibility questions, clearly identify:

- information that matches
- information that is missing
- information that does not match

IMPORTANT:

Do NOT convert percentage into percentile.

For example:

85% marks is NOT the same as 85 percentile.

Do not make a final government eligibility decision.

Do not add generic advice.

Keep the answer focused and concise.

End with:

"Final eligibility and approval are determined by the
concerned government authority."
"""


    # --------------------------------------------------------
    # DEBUG REQUEST
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("MULTIRAG LLM REQUEST")
    print("=" * 70)
    print("Model:", MODEL_NAME)
    print("Language:", language)
    print("Question:", question)
    print("Context characters:", len(context))
    print("API key loaded:", bool(OPENROUTER_API_KEY))
    print("=" * 70)


    # ========================================================
    # OPENROUTER CALL
    # ========================================================

    try:

        response = client.chat.completions.create(

            model=MODEL_NAME,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],

            temperature=0.1,

            max_tokens=1200,

        )


        # ----------------------------------------------------
        # RESPONSE DEBUG
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("MULTIRAG LLM RESPONSE")
        print("=" * 70)

        print(
            "Response received:",
            response is not None,
        )


        if response is None:

            return (
                "ERROR: OpenRouter returned no response."
            )


        choices = getattr(
            response,
            "choices",
            None,
        )

        print(
            "Choices:",
            len(choices) if choices else 0,
        )


        # ----------------------------------------------------
        # NO CHOICES
        # ----------------------------------------------------

        if not choices:

            print()
            print("FULL OPENROUTER RESPONSE:")
            print(
                _safe_response_debug(response)
            )

            print("=" * 70)

            return (
                "ERROR: OpenRouter returned no usable choices."
            )


        # ----------------------------------------------------
        # CHOICE DEBUG
        # ----------------------------------------------------

        choice = choices[0]

        print(
            "Finish reason:",
            getattr(
                choice,
                "finish_reason",
                None,
            ),
        )

        print(
            "Provider:",
            getattr(
                response,
                "provider",
                None,
            ),
        )

        print(
            "Model returned:",
            getattr(
                response,
                "model",
                None,
            ),
        )


        # ----------------------------------------------------
        # EXTRACT TEXT
        # ----------------------------------------------------

        answer = _extract_text_from_response(
            response
        )


        print()
        print("Extracted answer:")
        print(repr(answer))


        # ----------------------------------------------------
        # EMPTY CONTENT
        # ----------------------------------------------------

        if not answer:

            print()
            print(
                "WARNING: OPENROUTER RESPONSE "
                "CONTAINED NO TEXT"
            )

            print()
            print(
                "FULL OPENROUTER RESPONSE:"
            )

            print(
                _safe_response_debug(response)
            )

            print("=" * 70)
            print()


            # Return a more useful diagnostic.
            finish_reason = getattr(
                choice,
                "finish_reason",
                None,
            )

            if finish_reason:

                return (
                    "ERROR: OpenRouter returned no text content.\n\n"
                    f"Finish reason: {finish_reason}\n\n"
                    "Please try the request again."
                )

            return (
                "ERROR: OpenRouter returned no text content.\n\n"
                "Please try the request again."
            )


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        answer = answer.strip()

        print()
        print("FINAL ANSWER:")
        print(answer)

        print("=" * 70)
        print()


        return answer


    # ========================================================
    # ERROR
    # ========================================================

    except Exception as error:

        print()
        print("=" * 70)
        print("MULTIRAG LLM ERROR")
        print("=" * 70)

        print(
            "Exception type:",
            type(error).__name__,
        )

        print(
            "Exception:",
            repr(error),
        )

        print("=" * 70)
        print()


        return (
            "ERROR: The AI service could not generate "
            "an answer.\n\n"
            f"Technical details: {error}"
        )