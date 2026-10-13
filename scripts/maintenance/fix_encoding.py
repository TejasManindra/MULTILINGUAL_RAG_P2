from pathlib import Path


TEXT_DIR = Path("data/processed/text")


def repair_mojibake(text):
    replacements = {
        "Ã¢â‚¬â„¢": "’",
        "Ã¢â‚¬Å“": "“",
        "Ã¢â‚¬Â": "”",
        "Ã¢â‚¬â€œ": "–",
        "Ã¢â‚¬â€": "—",
        "Ã‚": "",
        "Â": "",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return text


def main():

    files = sorted(TEXT_DIR.glob("*.txt"))

    print(f"Found {len(files)} text files.")

    for file_path in files:

        text = file_path.read_text(
            encoding="utf-8"
        )

        repaired = repair_mojibake(text)

        file_path.write_text(
            repaired,
            encoding="utf-8"
        )

        print(f"Fixed: {file_path.name}")

    print("\nEncoding cleanup completed.")


if __name__ == "__main__":
    main()