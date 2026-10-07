import truststore

truststore.inject_into_ssl()

from pathlib import Path
import json
from sentence_transformers import SentenceTransformer




MODEL_NAME = "BAAI/bge-m3"
DATASET = Path("data/processed/unified/rag_documents.json")


def main():

    print("=" * 60)
    print("BGE-M3 EMBEDDING TEST")
    print("=" * 60)

    print(f"\nLoading model: {MODEL_NAME}")

    model = SentenceTransformer(
    MODEL_NAME,
    device="cpu",
    model_kwargs={
        "torch_dtype": "float32"
    }
)

    print("Model loaded successfully.")

    with open(DATASET, "r", encoding="utf-8") as f:
        documents = json.load(f)

    print(f"Dataset chunks: {len(documents)}")

    # Test only 3 chunks first
    texts = [
        doc["text"]
        for doc in documents[:3]
    ]

    print("\nGenerating test embeddings...")

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    print("\nEmbedding test successful.")

    print(f"Number of embeddings : {len(embeddings)}")
    print(f"Embedding dimension   : {len(embeddings[0])}")

    print("\nExpected dimension: 1024")

    if len(embeddings[0]) == 1024:
        print("Dimension check: PASS")
    else:
        print("Dimension check: FAIL")

    print("\nBGE-M3 test completed.")


if __name__ == "__main__":
    main()