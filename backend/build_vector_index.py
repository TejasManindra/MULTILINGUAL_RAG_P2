import uuid
import json
from pathlib import Path
from typing import List, Dict, Any

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

DATASET_FILE = (
    ROOT
    / "data"
    / "processed"
    / "unified"
    / "rag_documents.json"
)

MODEL_DIR = ROOT / "models" / "bge-m3"

QDRANT_DIR = (
    ROOT
    / "data"
    / "vector_db"
    / "qdrant"
)

COLLECTION_NAME = "multilingual_scheme_chunks"

VECTOR_SIZE = 1024

BATCH_SIZE = 16


# ============================================================
# LOAD DATASET
# ============================================================

def load_dataset() -> List[Dict[str, Any]]:
    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found:\n{DATASET_FILE}"
        )

    with open(
        DATASET_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError(
            "rag_documents.json must contain a list."
        )

    if len(records) != 1351:
        raise ValueError(
            f"Expected 1351 records, "
            f"found {len(records)}."
        )

    return records


# ============================================================
# VALIDATE DATASET
# ============================================================

def validate_records(records):
    chunk_ids = set()

    for record in records:

        required_fields = [
            "chunk_id",
            "scheme_id",
            "scheme_name",
            "government_level",
            "state",
            "text",
        ]

        missing = [
            field
            for field in required_fields
            if field not in record
        ]

        if missing:
            raise ValueError(
                f"{record.get('chunk_id')} "
                f"missing fields: {missing}"
            )

        chunk_id = record["chunk_id"]

        if chunk_id in chunk_ids:
            raise ValueError(
                f"Duplicate chunk_id: {chunk_id}"
            )

        chunk_ids.add(chunk_id)

        if not record["text"].strip():
            raise ValueError(
                f"Empty text: {chunk_id}"
            )

    print(
        f"Dataset validation passed: "
        f"{len(records)} records"
    )


# ============================================================
# LOAD MODEL
# ============================================================

def load_embedding_model():

    if not MODEL_DIR.exists():
        raise FileNotFoundError(
            f"BGE-M3 model not found:\n{MODEL_DIR}"
        )

    print()
    print("=" * 70)
    print("LOADING BGE-M3")
    print("=" * 70)

    model = SentenceTransformer(
        str(MODEL_DIR)
    )

    dimension = model.get_sentence_embedding_dimension()

    if dimension != VECTOR_SIZE:
        raise ValueError(
            f"Expected embedding dimension "
            f"{VECTOR_SIZE}, got {dimension}"
        )

    print(
        f"Embedding dimension: {dimension}"
    )

    return model


# ============================================================
# CREATE QDRANT
# ============================================================

def create_qdrant():

    QDRANT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 70)
    print("INITIALIZING QDRANT")
    print("=" * 70)

    client = QdrantClient(
        path=str(QDRANT_DIR)
    )

    collections = [
        collection.name
        for collection in client.get_collections().collections
    ]

    if COLLECTION_NAME in collections:

        print(
            f"Collection already exists: "
            f"{COLLECTION_NAME}"
        )

        existing_info = (
            client.get_collection(
                COLLECTION_NAME
            )
        )

        existing_count = (
            existing_info.points_count
        )

        print(
            f"Existing points: "
            f"{existing_count}"
        )

        print(
            "Recreating collection "
            "to guarantee consistency."
        )

        client.delete_collection(
            COLLECTION_NAME
        )

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE,
        ),
    )

    print(
        f"Created collection: "
        f"{COLLECTION_NAME}"
    )

    return client


# ============================================================
# BUILD PAYLOAD
# ============================================================

def build_payload(record):

    return {
        "chunk_id": record.get(
            "chunk_id"
        ),
        "scheme_id": record.get(
            "scheme_id"
        ),
        "scheme_name": record.get(
            "scheme_name"
        ),
        "government_level": record.get(
            "government_level"
        ),
        "state": record.get(
            "state"
        ),
        "ministry_department": record.get(
            "ministry_department"
        ),
        "category": record.get(
            "category"
        ),
        "subcategory": record.get(
            "subcategory"
        ),
        "target_beneficiary": record.get(
            "target_beneficiary"
        ),
        "scheme_status": record.get(
            "scheme_status"
        ),
        "benefit_description": record.get(
            "benefit_description"
        ),
        "eligibility_rules": record.get(
            "eligibility_rules"
        ),
        "exclusion_rules": record.get(
            "exclusion_rules"
        ),
        "verification_status": record.get(
            "verification_status"
        ),
        "source_url": record.get(
            "source_url"
        ),
        "source_status": record.get(
            "source_status"
        ),
        "source_file": record.get(
            "source_file"
        ),
        "document_title": record.get(
            "document_title"
        ),
        "page_number": record.get(
            "page_number"
        ),
        "chunk_number": record.get(
            "chunk_number"
        ),
        "text": record.get(
            "text"
        ),
    }


# ============================================================
# EMBED + INSERT
# ============================================================

def build_index(
    records,
    model,
    client,
):

    print()
    print("=" * 70)
    print("BUILDING VECTOR INDEX")
    print("=" * 70)

    total = len(records)

    inserted = 0

    for start in range(
        0,
        total,
        BATCH_SIZE,
    ):

        batch = records[
            start : start + BATCH_SIZE
        ]

        texts = [
            record["text"]
            for record in batch
        ]

        embeddings = model.encode(
            texts,
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        points = []

        for record, embedding in zip(
            batch,
            embeddings,
        ):

            point = PointStruct(
                id=str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        record["chunk_id"],
                    )
                ),
                vector=embedding.tolist(),
                payload=build_payload(
                    record
                ),
            )

            points.append(point)

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
            wait=True,
        )

        inserted += len(points)

        percent = (
            inserted / total
        ) * 100

        print(
            f"Indexed {inserted}/{total} "
            f"({percent:.1f}%)"
        )

    return inserted


# ============================================================
# VERIFY INDEX
# ============================================================

def verify_index(
    client,
    expected_count,
):

    print()
    print("=" * 70)
    print("VERIFYING QDRANT INDEX")
    print("=" * 70)

    info = client.get_collection(
        COLLECTION_NAME
    )

    actual_count = info.points_count

    print(
        f"Expected points : "
        f"{expected_count}"
    )

    print(
        f"Actual points   : "
        f"{actual_count}"
    )

    if actual_count != expected_count:

        raise RuntimeError(
            "Qdrant point count mismatch!"
        )

    print(
        "QDRANT VALIDATION PASSED"
    )


# ============================================================
# TEST SEARCH
# ============================================================

def test_search(
    client,
    model,
    query,
):

    print()
    print("=" * 70)
    print("TEST QUERY")
    print("=" * 70)

    print(
        f"Query: {query}"
    )

    query_embedding = model.encode(
        query,
        normalize_embeddings=True,
    )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding.tolist(),
        limit=5,
        with_payload=True,
    ).points

    print()
    print("TOP RESULTS")
    print("-" * 70)

    for rank, result in enumerate(
        results,
        start=1,
    ):

        payload = result.payload or {}

        print(
            f"\n{rank}. "
            f"{payload.get('scheme_name')}"
        )

        print(
            f"   Score      : "
            f"{result.score:.4f}"
        )

        print(
            f"   Scheme ID  : "
            f"{payload.get('scheme_id')}"
        )

        print(
            f"   State      : "
            f"{payload.get('state')}"
        )

        print(
            f"   Level      : "
            f"{payload.get('government_level')}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("MULTILINGUAL RAG - BGE-M3 VECTOR INDEX BUILDER")
    print("=" * 70)

    # --------------------------------------------------------
    # Dataset
    # --------------------------------------------------------

    records = load_dataset()

    print(
        f"\nLoaded records: "
        f"{len(records)}"
    )

    validate_records(
        records
    )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    model = load_embedding_model()

    # --------------------------------------------------------
    # Qdrant
    # --------------------------------------------------------

    client = create_qdrant()

    # --------------------------------------------------------
    # Index
    # --------------------------------------------------------

    inserted = build_index(
        records,
        model,
        client,
    )

    print()
    print(
        f"Inserted points: "
        f"{inserted}"
    )

    # --------------------------------------------------------
    # Verify
    # --------------------------------------------------------

    verify_index(
        client,
        len(records),
    )

    # --------------------------------------------------------
    # English test
    # --------------------------------------------------------

    test_search(
        client,
        model,
        "PM KISAN eligibility for farmers",
    )

    # --------------------------------------------------------
    # Telugu test
    # --------------------------------------------------------

    test_search(
        client,
        model,
        "రైతులకు పీఎం కిసాన్ పథకం అర్హత ఏమిటి",
    )

    print()
    print("=" * 70)
    print("VECTOR INDEX BUILD COMPLETE")
    print("=" * 70)

    print(
        f"Qdrant location: "
        f"{QDRANT_DIR}"
    )

    print(
        f"Collection: "
        f"{COLLECTION_NAME}"
    )

    print(
        f"Vectors: "
        f"{len(records)}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()