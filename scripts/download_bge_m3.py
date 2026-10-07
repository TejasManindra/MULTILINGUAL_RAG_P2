import truststore

truststore.inject_into_ssl()

from huggingface_hub import snapshot_download


MODEL_NAME = "BAAI/bge-m3"


print("Starting BGE-M3 download...")

path = snapshot_download(
    repo_id=MODEL_NAME,
    force_download=True,
    max_workers=1,
)

print("\nDownload completed.")
print("Model path:", path)