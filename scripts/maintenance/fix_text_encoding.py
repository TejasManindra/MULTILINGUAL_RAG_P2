from pathlib import Path


TEXT_DIR = Path("data/processed/text")


def repair_mojibake(text):
    """
    Repair UTF-8 text that was decoded incorrectly
    as Windows-1252.
    """

    replacements = {
        "â€™": "’",
        "â€œ": "“",
        "â€": "”",
        "â€“": "–",
        "â€”": "—",
        "â€¦": "…",
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

    print("\nEncoding repair completed.")


if __name__ == "__main__":
    main()