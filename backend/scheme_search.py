import re
import unicodedata
from pathlib import Path

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

QDRANT_PATH = BASE_DIR / "data" / "vector_db" / "qdrant"
MODEL_PATH = BASE_DIR / "models" / "bge-m3"

COLLECTION_NAME = "multilingual_scheme_chunks"

# Number of semantic chunks retrieved from BGE-M3
TOP_K_VECTOR = 30

# Number of final schemes returned
TOP_K_FINAL = 8

# Boost applied when the detected scheme matches
EXACT_BOOST = 0.30

# Number of chunks retrieved directly when an exact
# scheme name is detected
EXACT_SCHEME_CHUNKS = 30

# Number of exact-scheme chunks kept after BGE-M3 reranking
EXACT_RERANK_TOP_K = 8

# Maximum chunks retained per scheme after aggregation
MAX_CHUNKS_PER_SCHEME = 8


# ============================================================
# SCHEME ALIASES
# English + Telugu
# ============================================================

SCHEME_ALIASES = {

    # --------------------------------------------------------
    # CENTRAL
    # --------------------------------------------------------

    "PM_KISAN": [
        "pm kisan",
        "pm-kisan",
        "pmkisan",
        "pradhan mantri kisan samman nidhi",
        "pm kisan samman nidhi",

        # Telugu
        "పీఎం కిసాన్",
        "పిఎం కిసాన్",
        "పీఎంకిసాన్",
        "పిఎంకిసాన్",
        "పీఎం కిసాన్ పథకం",
        "పిఎం కిసాన్ పథకం",
    ],

    "KCC": [
        "kisan credit card",
        "kisan credit card scheme",
        "kcc",

        # Telugu
        "కిసాన్ క్రెడిట్ కార్డ్",
        "కిసాన్ క్రెడిట్ కార్డు",
    ],

    # --------------------------------------------------------
    # ANDHRA PRADESH
    # --------------------------------------------------------

    "AP_AP_NTR_BHAROSA": [
        "ntr bharosa",
        "ntr bharosa pension",
        "ntr bharosa pension scheme",

        # Telugu
        "ఎన్టీఆర్ భరోసా",
        "ఎన్టీఆర్ భరోసా పెన్షన్",
        "ఎన్టీఆర్ భరోసా పింఛన్",
    ],

    "AP_THALLIKI_VANDANAM": [
        "thalliki vandanam",
        "thalliki vandanam scheme",

        # Telugu
        "తల్లికి వందనం",
        "తల్లికి వందనం పథకం",
    ],

    "AP_DEEPAM_2": [
        "deepam",
        "deepam 2",
        "deepam 2.0",
        "deepam scheme",

        # Telugu
        "దీపం",
        "దీపం 2.0",
        "దీపం పథకం",
    ],

    "AP_STREE_SHAKTI": [
        "stree shakti",
        "stree shakti scheme",

        # Telugu
        "స్త్రీ శక్తి",
        "స్త్రీ శక్తి పథకం",
    ],

    "AP_ANNADATA_SUKHIBHAVA_PM_KISAN": [
        "annadata sukhibhava",
        "annadata sukhibhava pm kisan",
        "annadata sukhibhava pm-kisan",

        # Telugu
        "అన్నదాత సుఖీభవ",
        "అన్నదాత సుఖీభవ పీఎం కిసాన్",
        "అన్నదాత సుఖీభవ పిఎం కిసాన్",
    ],

    # --------------------------------------------------------
    # TELANGANA
    # --------------------------------------------------------

    "TS_RYTHU_BHAROSA_AGRICULTURE_SUPPORT": [
        "rythu bharosa",
        "rythu bharosa telangana",

        # Telugu
        "రైతు భరోసా",
        "తెలంగాణ రైతు భరోసా",
    ],

    "TS_GRUHA_JYOTHI_SCHEME": [
        "gruha jyothi",
        "gruha jyoti",

        # Telugu
        "గృహ జ్యోతి",
        "గృహ జ్యోతి పథకం",
    ],

    "TS_MAHA_LAKSHMI_SCHEME": [
        "maha lakshmi",
        "mahalakshmi",

        # Telugu
        "మహాలక్ష్మి",
        "మహా లక్ష్మి",
    ],

    "TS_KALYANA_LAKSHMI_PATHAKAM": [
        "kalyana lakshmi",
        "kalyana lakshmi pathakam",

        # Telugu
        "కల్యాణ లక్ష్మి",
        "కళ్యాణ లక్ష్మి",
    ],

    "TS_SHAADI_MUBARAK_SCHEME_FOR_MINORITIES": [
        "shaadi mubarak",
        "shadi mubarak",

        # Telugu
        "షాదీ ముబారక్",
    ],

    "TS_TELANGANA_CHEYUTHA_SCHEME": [
        "cheyutha",
        "cheyutha scheme",

        # Telugu
        "చేయూత",
        "చేయూత పథకం",
    ],

    "TS_RAJIV_AAROGYASRI_COMMUNITY_HEALTH_INSURANCE_SCHEME": [
        "aarogyasri",
        "rajiv aarogyasri",
        "rajiv aarogyasri scheme",

        # Telugu
        "ఆరోగ్యశ్రీ",
        "రాజీవ్ ఆరోగ్యశ్రీ",
    ],
}


# ============================================================
# NORMALIZE ALIASES
# ============================================================

NORMALIZED_ALIASES = {}

for scheme_id, aliases in SCHEME_ALIASES.items():

    NORMALIZED_ALIASES[scheme_id] = [
        unicodedata.normalize(
            "NFC",
            alias.lower().strip()
        )
        for alias in aliases
    ]


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:
    """
    Normalize English and Telugu text.

    Telugu Unicode characters are preserved.
    """

    if not text:
        return ""

    text = unicodedata.normalize(
        "NFC",
        text
    )

    text = text.lower().strip()

    # Normalize different dash characters
    text = re.sub(
        r"[-‐-‒–—―]",
        "-",
        text
    )

    # Collapse repeated whitespace
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# ============================================================
# SCHEME DETECTION
# ============================================================

def detect_scheme_id(query: str):
    """
    Detect an explicitly mentioned scheme.

    Works with English and Telugu aliases.

    The longest matching alias wins.
    """

    normalized_query = normalize_text(
        query
    )

    matches = []

    for scheme_id, aliases in NORMALIZED_ALIASES.items():

        for alias in aliases:

            if not alias:
                continue

            if alias in normalized_query:

                matches.append(
                    (
                        scheme_id,
                        len(alias)
                    )
                )

    if not matches:
        return None

    # Longest alias = strongest exact match
    matches.sort(
        key=lambda item: item[1],
        reverse=True
    )

    return matches[0][0]


# ============================================================
# STATE DETECTION
# ============================================================

STATE_ALIASES = {

    "telangana": [
        "telangana",
        "ts",
        "తెలంగాణ",
        "తెలంగాణ రాష్ట్రం",
    ],

    "andhra pradesh": [
        "andhra pradesh",
        "andhra",
        "ap",
        "ఆంధ్రప్రదేశ్",
        "ఆంధ్ర ప్రదేశ్",
        "ఆంధ్ర",
    ],
}


NORMALIZED_STATE_ALIASES = {
    state: [
        normalize_text(alias)
        for alias in aliases
    ]
    for state, aliases in STATE_ALIASES.items()
}


def detect_state(query: str):
    """
    Detect an explicitly mentioned state.

    Returns:
        "telangana"
        "andhra pradesh"
        None
    """

    normalized_query = normalize_text(
        query
    )

    matches = []

    for state, aliases in NORMALIZED_STATE_ALIASES.items():

        for alias in aliases:

            if not alias:
                continue

            # Avoid treating very short aliases such as
            # "ap" or "ts" as matches inside larger words.
            if alias in {"ap", "ts"}:

                if re.search(
                    rf"\b{re.escape(alias)}\b",
                    normalized_query
                ):

                    matches.append(
                        (
                            state,
                            len(alias)
                        )
                    )

            elif alias in normalized_query:

                matches.append(
                    (
                        state,
                        len(alias)
                    )
                )

    if not matches:
        return None

    matches.sort(
        key=lambda item: item[1],
        reverse=True
    )

    return matches[0][0]


# ============================================================
# VECTOR SEARCH
# ============================================================

def vector_search(
    query: str,
    client: QdrantClient,
    model: SentenceTransformer,
    limit: int = TOP_K_VECTOR,
):
    """
    Semantic BGE-M3 vector search.
    """

    query_vector = model.encode(
        query,
        normalize_embeddings=True
    ).tolist()

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )

    return response.points


# ============================================================
# EXACT SCHEME SEARCH
# ============================================================

def exact_scheme_search(
    scheme_id: str,
    client: QdrantClient,
    limit: int = EXACT_SCHEME_CHUNKS,
):
    """
    Retrieve chunks directly belonging to the detected scheme.

    Uses Qdrant Filter objects.
    """

    from qdrant_client.models import (
        Filter,
        FieldCondition,
        MatchValue,
    )

    scroll_filter = Filter(
        must=[
            FieldCondition(
                key="scheme_id",
                match=MatchValue(
                    value=scheme_id
                ),
            )
        ]
    )

    points, next_offset = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=scroll_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    return points


# ============================================================
# RERANK EXACT SCHEME CHUNKS
# ============================================================

def rerank_exact_chunks(
    query: str,
    exact_results,
    model: SentenceTransformer,
    limit: int = EXACT_RERANK_TOP_K,
):
    """
    Re-rank chunks belonging to the explicitly detected scheme
    using BGE-M3 semantic similarity.

    This prevents all chunks from an exact scheme from being
    passed downstream. Only the most relevant chunks are kept.
    """

    if not exact_results:
        return []

    texts = []
    valid_results = []

    for result in exact_results:

        payload = result.payload or {}

        text = payload.get("text")

        if not text:
            continue

        texts.append(text)
        valid_results.append(result)

    if not texts:
        return []

    # --------------------------------------------------------
    # Encode query
    # --------------------------------------------------------

    query_vector = model.encode(
        query,
        normalize_embeddings=True
    )

    # --------------------------------------------------------
    # Encode exact-scheme chunks
    # --------------------------------------------------------

    chunk_vectors = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=16,
        show_progress_bar=False,
    )

    # --------------------------------------------------------
    # Cosine similarity
    # --------------------------------------------------------

    scores = chunk_vectors @ query_vector

    reranked = []

    for result, score in zip(
        valid_results,
        scores
    ):

        reranked.append(
            {
                "result": result,
                "vector_score": float(score),
                "source": "exact_reranked",
            }
        )

    # Highest semantic relevance first
    reranked.sort(
        key=lambda item: item["vector_score"],
        reverse=True
    )

    return reranked[:limit]


# ============================================================
# STATE SCORE
# ============================================================

def calculate_state_bonus(
    result_state,
    detected_state,
    government_level,
):
    """
    Score a result based on explicitly detected state.

    Central schemes remain eligible when a state is mentioned.

    State-specific schemes matching the requested state receive
    a positive bonus.

    A scheme belonging to another state receives a penalty.
    """

    if not detected_state:
        return 0.0

    normalized_result_state = normalize_text(
        result_state or ""
    )

    normalized_detected_state = normalize_text(
        detected_state
    )

    # Central schemes are still allowed.
    if government_level == "central":
        return 0.0

    # Exact state match.
    if normalized_result_state == normalized_detected_state:
        return 0.15

    # Wrong state.
    if normalized_result_state:
        return -0.20

    return 0.0


# ============================================================
# HYBRID SEARCH
# ============================================================

def hybrid_search(
    query: str,
    top_k: int = TOP_K_FINAL
):
    """
    Hybrid retrieval pipeline:

        Query
          ↓
        Scheme detection
          ↓
        State detection
          ↓
        BGE-M3 semantic search
          ↓
        Exact scheme retrieval
          ↓
        BGE-M3 exact-chunk reranking
          ↓
        Merge + deduplicate
          ↓
        Hybrid scoring
          ↓
        State-aware scoring
          ↓
        Scheme aggregation
          ↓
        Final ranking
    """

    # --------------------------------------------------------
    # Open Qdrant
    # --------------------------------------------------------

    client = QdrantClient(
        path=str(QDRANT_PATH)
    )

    # --------------------------------------------------------
    # Load BGE-M3
    # --------------------------------------------------------

    model = SentenceTransformer(
        str(MODEL_PATH)
    )

    # --------------------------------------------------------
    # Detect scheme
    # --------------------------------------------------------

    detected_scheme = detect_scheme_id(
        query
    )

    # --------------------------------------------------------
    # Detect state
    # --------------------------------------------------------

    detected_state = detect_state(
        query
    )

    # --------------------------------------------------------
    # Semantic retrieval
    # --------------------------------------------------------

    vector_results = vector_search(
        query=query,
        client=client,
        model=model,
        limit=TOP_K_VECTOR,
    )

    # --------------------------------------------------------
    # Exact scheme retrieval + reranking
    # --------------------------------------------------------

    exact_results = []

    if detected_scheme:

        raw_exact_results = exact_scheme_search(
            scheme_id=detected_scheme,
            client=client,
            limit=EXACT_SCHEME_CHUNKS,
        )

        exact_results = rerank_exact_chunks(
            query=query,
            exact_results=raw_exact_results,
            model=model,
            limit=EXACT_RERANK_TOP_K,
        )

    # --------------------------------------------------------
    # Merge results
    # --------------------------------------------------------

    merged = {}

    # --------------------------------------------------------
    # Semantic results
    # --------------------------------------------------------

    for result in vector_results:

        payload = result.payload or {}

        chunk_id = payload.get(
            "chunk_id"
        )

        if not chunk_id:
            continue

        merged[chunk_id] = {
            "result": result,
            "vector_score": float(
                result.score
            ),
            "source": "semantic",
        }

    # --------------------------------------------------------
    # Exact reranked results
    # --------------------------------------------------------

    for item in exact_results:

        result = item["result"]

        payload = result.payload or {}

        chunk_id = payload.get(
            "chunk_id"
        )

        if not chunk_id:
            continue

        reranked_score = item[
            "vector_score"
        ]

        # If the same chunk was already found by semantic
        # search, retain whichever BGE-M3 score is stronger.
        if chunk_id in merged:

            existing_score = merged[
                chunk_id
            ]["vector_score"]

            if reranked_score > existing_score:

                merged[chunk_id] = {
                    "result": result,
                    "vector_score": reranked_score,
                    "source": "exact_reranked",
                }

            continue

        merged[chunk_id] = {
            "result": result,
            "vector_score": reranked_score,
            "source": "exact_reranked",
        }

    # --------------------------------------------------------
    # Hybrid scoring
    # --------------------------------------------------------

    scored_results = []

    for item in merged.values():

        result = item["result"]

        payload = result.payload or {}

        scheme_id = payload.get(
            "scheme_id"
        )

        if not scheme_id:
            continue

        vector_score = item[
            "vector_score"
        ]

        government_level = payload.get(
            "government_level"
        )

        result_state = payload.get(
            "state"
        )

        # ----------------------------------------------------
        # Exact scheme match
        # ----------------------------------------------------

        exact_match = (
            detected_scheme is not None
            and scheme_id == detected_scheme
        )

        exact_boost = (
            EXACT_BOOST
            if exact_match
            else 0.0
        )

        # ----------------------------------------------------
        # State score
        # ----------------------------------------------------

        state_bonus = calculate_state_bonus(
            result_state=result_state,
            detected_state=detected_state,
            government_level=government_level,
        )

        # ----------------------------------------------------
        # Base score
        # ----------------------------------------------------

        base_score = vector_score

        # ----------------------------------------------------
        # Final score
        # ----------------------------------------------------

        final_score = (
            base_score
            + exact_boost
            + state_bonus
        )

        scored_results.append(
            {
                "result": result,

                "scheme_id": scheme_id,

                "vector_score": vector_score,

                "exact_match": exact_match,

                "exact_boost": exact_boost,

                "state_bonus": state_bonus,

                "final_score": final_score,

                "source": item["source"],
            }
        )

    # --------------------------------------------------------
    # Sort chunks by final score
    # --------------------------------------------------------

    scored_results.sort(
        key=lambda item: item["final_score"],
        reverse=True
    )

    # --------------------------------------------------------
    # Aggregate by scheme
    # --------------------------------------------------------

    aggregated = {}

    for item in scored_results:

        result = item["result"]

        payload = result.payload or {}

        scheme_id = item[
            "scheme_id"
        ]

        # ----------------------------------------------------
        # Create scheme-level record
        # ----------------------------------------------------

        if scheme_id not in aggregated:

            aggregated[scheme_id] = {

                # ------------------------------------------------
                # Identity
                # ------------------------------------------------

                "scheme_id": scheme_id,

                "scheme_name": payload.get(
                    "scheme_name",
                    "Unknown"
                ),

                # ------------------------------------------------
                # Government / geography
                # ------------------------------------------------

                "government_level": payload.get(
                    "government_level"
                ),

                "state": payload.get(
                    "state"
                ),

                # ------------------------------------------------
                # Scheme classification
                # ------------------------------------------------

                "ministry_department": payload.get(
                    "ministry_department"
                ),

                "category": payload.get(
                    "category"
                ),

                "subcategory": payload.get(
                    "subcategory"
                ),

                "target_beneficiary": payload.get(
                    "target_beneficiary"
                ),

                # ------------------------------------------------
                # Scheme status
                # ------------------------------------------------

                "scheme_status": payload.get(
                    "scheme_status"
                ),

                "verification_status": payload.get(
                    "verification_status"
                ),

                "source_status": payload.get(
                    "source_status"
                ),

                # ------------------------------------------------
                # Scheme content
                # ------------------------------------------------

                "benefit_description": payload.get(
                    "benefit_description"
                ),

                # IMPORTANT:
                # Preserve structured deterministic rules.
                "eligibility_rules": payload.get(
                    "eligibility_rules"
                ),

                "exclusion_rules": payload.get(
                    "exclusion_rules"
                ),

                # ------------------------------------------------
                # Source information
                # ------------------------------------------------

                "source_url": payload.get(
                    "source_url"
                ),

                "source_file": payload.get(
                    "source_file"
                ),

                "document_title": payload.get(
                    "document_title"
                ),

                # ------------------------------------------------
                # Retrieval scores
                # ------------------------------------------------

                "vector_score": item[
                    "vector_score"
                ],

                "exact_boost": item[
                    "exact_boost"
                ],

                "state_bonus": item[
                    "state_bonus"
                ],

                "final_score": item[
                    "final_score"
                ],

                "exact_match": item[
                    "exact_match"
                ],

                # ------------------------------------------------
                # Retrieved chunks
                # ------------------------------------------------

                "chunks": [],
            }

        # ----------------------------------------------------
        # Preserve metadata from every chunk
        # ----------------------------------------------------

        scheme = aggregated[scheme_id]

        # Only fill metadata if it is currently missing.
        # This avoids accidentally replacing valid metadata.
        scheme["scheme_name"] = (
            scheme.get("scheme_name")
            or payload.get("scheme_name")
        )

        scheme["government_level"] = (
            scheme.get("government_level")
            or payload.get("government_level")
        )

        scheme["state"] = (
            scheme.get("state")
            or payload.get("state")
        )

        scheme["ministry_department"] = (
            scheme.get("ministry_department")
            or payload.get("ministry_department")
        )

        scheme["category"] = (
            scheme.get("category")
            or payload.get("category")
        )

        scheme["subcategory"] = (
            scheme.get("subcategory")
            or payload.get("subcategory")
        )

        scheme["target_beneficiary"] = (
            scheme.get("target_beneficiary")
            or payload.get("target_beneficiary")
        )

        scheme["scheme_status"] = (
            scheme.get("scheme_status")
            or payload.get("scheme_status")
        )

        scheme["verification_status"] = (
            scheme.get("verification_status")
            or payload.get("verification_status")
        )

        scheme["source_status"] = (
            scheme.get("source_status")
            or payload.get("source_status")
        )

        scheme["benefit_description"] = (
            scheme.get("benefit_description")
            or payload.get("benefit_description")
        )

        scheme["source_url"] = (
            scheme.get("source_url")
            or payload.get("source_url")
        )

        scheme["source_file"] = (
            scheme.get("source_file")
            or payload.get("source_file")
        )

        scheme["document_title"] = (
            scheme.get("document_title")
            or payload.get("document_title")
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # Preserve eligibility rules if they appear in ANY
        # retrieved chunk.
        # ----------------------------------------------------

        if (
            not scheme.get("eligibility_rules")
            and payload.get("eligibility_rules")
        ):
            scheme["eligibility_rules"] = (
                payload.get("eligibility_rules")
            )

        # ----------------------------------------------------
        # Preserve exclusion rules
        # ----------------------------------------------------

        if (
            not scheme.get("exclusion_rules")
            and payload.get("exclusion_rules")
        ):
            scheme["exclusion_rules"] = (
                payload.get("exclusion_rules")
            )

        # ----------------------------------------------------
        # Keep strongest scheme-level score
        # ----------------------------------------------------

        if (
            item["final_score"]
            > scheme["final_score"]
        ):

            scheme["final_score"] = (
                item["final_score"]
            )

            scheme["vector_score"] = (
                item["vector_score"]
            )

            scheme["exact_boost"] = (
                item["exact_boost"]
            )

            scheme["state_bonus"] = (
                item["state_bonus"]
            )

            scheme["exact_match"] = (
                item["exact_match"]
            )

        # ----------------------------------------------------
        # Store chunk
        # ----------------------------------------------------

        scheme["chunks"].append(
            {
                "chunk_id": payload.get(
                    "chunk_id"
                ),

                "score": item[
                    "final_score"
                ],

                "text": payload.get(
                    "text"
                ),

                "page_number": payload.get(
                    "page_number"
                ),

                "document_title": payload.get(
                    "document_title"
                ),
            }
        )

    # --------------------------------------------------------
    # Limit chunks per scheme
    # --------------------------------------------------------

    for scheme in aggregated.values():

        scheme["chunks"].sort(
            key=lambda chunk: chunk["score"],
            reverse=True
        )

        scheme["chunks"] = scheme[
            "chunks"
        ][:MAX_CHUNKS_PER_SCHEME]

    # --------------------------------------------------------
    # Final scheme ranking
    # --------------------------------------------------------

    final_results = list(
        aggregated.values()
    )

    final_results.sort(
        key=lambda item: item["final_score"],
        reverse=True
    )

    return (
        detected_scheme,
        detected_state,
        final_results[:top_k]
    )


# ============================================================
# DEBUG DISPLAY
# ============================================================

def print_results(
    query: str,
    detected_scheme,
    detected_state,
    results
):

    print("\n" + "=" * 70)
    print("HYBRID SCHEME SEARCH")
    print("=" * 70)

    print(
        f"Query          : {query}"
    )

    print(
        f"Detected scheme: {detected_scheme}"
    )

    print(
        f"Detected state : {detected_state}"
    )

    print("\nSCHEME RESULTS")
    print("-" * 70)

    if not results:

        print("\nNo results found.")

        return

    for i, item in enumerate(
        results,
        start=1
    ):

        print(
            f"\n{i}. "
            f"{item['scheme_name']}"
        )

        print(
            f"   Scheme ID   : "
            f"{item['scheme_id']}"
        )

        print(
            f"   State       : "
            f"{item['state']}"
        )

        print(
            f"   Government  : "
            f"{item['government_level']}"
        )

        print(
            f"   Vector      : "
            f"{item['vector_score']:.4f}"
        )

        print(
            f"   Exact match : "
            f"{item['exact_match']}"
        )

        print(
            f"   Exact boost : "
            f"{item['exact_boost']:.2f}"
        )

        print(
            f"   State bonus : "
            f"{item['state_bonus']:.2f}"
        )

        print(
            f"   Final       : "
            f"{item['final_score']:.4f}"
        )

        print(
            f"   Rules       : "
            f"{'PRESENT' if item.get('eligibility_rules') else 'MISSING'}"
        )

        print(
            f"   Chunks      : "
            f"{len(item['chunks'])}"
        )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_queries = [

        # ----------------------------------------------------
        # Central
        # ----------------------------------------------------

        "PM KISAN eligibility for farmers",

        "రైతులకు పీఎం కిసాన్ పథకం అర్హత ఏమిటి",

        "Kisan Credit Card eligibility",

        # ----------------------------------------------------
        # Andhra Pradesh
        # ----------------------------------------------------

        "What is Thalliki Vandanam?",

        "తల్లికి వందనం పథకం అర్హత ఏమిటి",

        "Thalliki Vandanam in Andhra Pradesh",

        # ----------------------------------------------------
        # Telangana
        # ----------------------------------------------------

        "రైతు భరోసా పథకం తెలంగాణ",

        "Rythu Bharosa in Telangana",

        "Gruha Jyothi Telangana",

        "గృహ జ్యోతి తెలంగాణ",
    ]

    for query in test_queries:

        (
            detected_scheme,
            detected_state,
            results
        ) = hybrid_search(
            query
        )

        print_results(
            query=query,
            detected_scheme=detected_scheme,
            detected_state=detected_state,
            results=results
        )