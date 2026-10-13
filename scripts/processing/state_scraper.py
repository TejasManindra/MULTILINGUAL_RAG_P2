from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime
import hashlib
import json
import re
import time

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIG
# ============================================================

MANIFEST = Path("data/config/state_schemes.json")

RAW_DIR = Path("data/raw")
HISTORICAL_DIR = Path("data/raw/historical")

METADATA_FILE = Path(
    "data/metadata/state_documents.json"
)

REQUEST_TIMEOUT = 30
CRAWL_DELAY = 1.0

MAX_PAGES_PER_DOMAIN = 80
MAX_DEPTH = 2

CURRENT_YEAR = datetime.now().year

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


# ============================================================
# REQUEST
# ============================================================

session = requests.Session()
session.headers.update(HEADERS)


def fetch(url):
    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )

        response.raise_for_status()

        return response

    except Exception as exc:
        print(f"    ERROR: {url}")
        print(f"           {exc}")
        return None


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_name(text):
    text = normalize_text(text).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    return text.strip()


def scheme_matches(text, scheme):
    """
    Require the actual scheme name or alias
    to occur in the page/PDF-related text.
    """

    text_norm = normalize_name(text)

    candidates = [
        scheme["scheme_name"]
    ] + scheme.get("aliases", [])

    for candidate in candidates:

        candidate_norm = normalize_name(
            candidate
        )

        if candidate_norm and candidate_norm in text_norm:
            return True

    return False


def safe_filename(name):
    name = re.sub(
        r'[<>:"/\\|?*]',
        "",
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name.strip(" .")[:180]


# ============================================================
# DOMAIN CHECK
# ============================================================

def domain_allowed(url, allowed_domains):

    hostname = urlparse(url).hostname

    if not hostname:
        return False

    hostname = hostname.lower()

    for domain in allowed_domains:

        domain = domain.lower()

        if (
            hostname == domain
            or hostname.endswith("." + domain)
        ):
            return True

    return False


# ============================================================
# DATE EXTRACTION
# ============================================================

DATE_PATTERNS = [
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
    r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},\s+\d{4}\b",
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{4}\b"
]


def extract_dates(text):

    dates = []

    for pattern in DATE_PATTERNS:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        dates.extend(matches)

    return list(dict.fromkeys(dates))


def parse_years(text):

    years = re.findall(
        r"\b20\d{2}\b",
        text
    )

    return sorted(
        set(int(y) for y in years)
    )


# ============================================================
# FRESHNESS
# ============================================================

def freshness_score(
    text,
    response=None,
    source_url=""
):

    """
    This is deliberately conservative.

    CURRENT:
        Strong evidence of current-year material.

    CURRENT_UNDATED:
        Official active page but no reliable date.

    HISTORICAL:
        Clearly old material with no current signal.
    """

    years = parse_years(text)

    current_year_present = (
        CURRENT_YEAR in years
        or (CURRENT_YEAR - 1) in years
    )

    # Current-year URL is a useful signal
    url_current = (
        str(CURRENT_YEAR) in source_url
    )

    # Explicit current language
    current_terms = [
        "2026-27",
        "2026–27",
        "2026/27",
        "2026-2027",
        "current year",
        "currently implemented",
        "being implemented",
        "with effect from 2026",
        "effective from 2026"
    ]

    current_language = any(
        term.lower() in text.lower()
        for term in current_terms
    )

    # Old indicators
    historical_terms = [
        "discontinued",
        "superseded",
        "historical",
        "closed scheme",
        "scheme closed",
        "up to 2019",
        "up to 2020",
        "up to 2021",
        "up to 2022",
        "up to 2023"
    ]

    historical_language = any(
        term.lower() in text.lower()
        for term in historical_terms
    )

    if (
        current_year_present
        or url_current
        or current_language
    ):
        return {
            "status": "CURRENT",
            "score": 3
        }

    if historical_language:
        return {
            "status": "HISTORICAL",
            "score": 0
        }

    # Official active page without date
    if response is not None:
        last_modified = response.headers.get(
            "Last-Modified"
        )

        if last_modified:
            return {
                "status": "CURRENT_UNDATED",
                "score": 2,
                "last_modified": last_modified
            }

    return {
        "status": "CURRENT_UNDATED",
        "score": 1
    }


# ============================================================
# TITLE EXTRACTION
# ============================================================

def extract_title(soup):

    h1 = soup.find("h1")

    if h1:
        title = normalize_text(
            h1.get_text(" ", strip=True)
        )

        if title:
            return title

    og = soup.find(
        "meta",
        attrs={"property": "og:title"}
    )

    if og and og.get("content"):
        return normalize_text(
            og["content"]
        )

    if soup.title:
        return normalize_text(
            soup.title.get_text(
                " ",
                strip=True
            )
        )

    return ""


# ============================================================
# PDF
# ============================================================

def is_pdf(url, response=None):

    if ".pdf" in url.lower():
        return True

    if response:

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        return "application/pdf" in content_type

    return False


def save_pdf(
    response,
    scheme,
    state,
    source_url,
    source_page,
    freshness
):

    state_dir = RAW_DIR / state

    state_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = (
        safe_filename(
            scheme["scheme_name"]
        )
        + ".pdf"
    )

    output = state_dir / filename

    # Don't overwrite an existing file
    if output.exists():
        print(
            f"      EXISTS: {output.name}"
        )
        return False

    output.write_bytes(
        response.content
    )

    print(
        f"      SAVED: {output.name}"
    )

    save_metadata({
        "scheme_id": scheme["scheme_id"],
        "scheme_name": scheme["scheme_name"],
        "state": state,
        "category": scheme["category"],
        "priority": scheme["priority"],
        "source_url": source_url,
        "source_page": source_page,
        "local_file": str(output),
        "document_type": "PDF",
        "freshness_status": freshness["status"],
        "freshness_score": freshness["score"],
        "download_date": datetime.now().isoformat(
            timespec="seconds"
        ),
        "sha256": hashlib.sha256(
            response.content
        ).hexdigest(),
        "file_size_bytes": len(
            response.content
        )
    })

    return True


# ============================================================
# HTML SNAPSHOT
# ============================================================

def save_html(
    soup,
    scheme,
    state,
    source_url,
    freshness
):

    state_dir = RAW_DIR / state

    state_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    filename = (
        safe_filename(
            scheme["scheme_name"]
        )
        + ".json"
    )

    output = state_dir / filename

    if output.exists():
        return False

    text = normalize_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    record = {
        "scheme_id": scheme["scheme_id"],
        "scheme_name": scheme["scheme_name"],
        "state": state,
        "category": scheme["category"],
        "priority": scheme["priority"],
        "source_url": source_url,
        "document_type": "HTML",
        "title": extract_title(soup),
        "text": text,
        "freshness_status": freshness["status"],
        "freshness_score": freshness["score"],
        "download_date": datetime.now().isoformat(
            timespec="seconds"
        )
    }

    output.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"      SAVED HTML: {output.name}"
    )

    save_metadata(record)

    return True


# ============================================================
# METADATA
# ============================================================

def save_metadata(record):

    METADATA_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    records = []

    if METADATA_FILE.exists():

        try:
            records = json.loads(
                METADATA_FILE.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:
            records = []

    # Deduplicate by source URL + scheme
    key = (
        record["scheme_id"],
        record["source_url"]
    )

    records = [
        r for r in records
        if (
            r.get("scheme_id"),
            r.get("source_url")
        ) != key
    ]

    records.append(record)

    METADATA_FILE.write_text(
        json.dumps(
            records,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


# ============================================================
# PAGE PROCESSING
# ============================================================

def process_page(
    url,
    state,
    scheme,
    visited,
    queue,
    depth
):

    if url in visited:
        return

    if depth > MAX_DEPTH:
        return

    if not domain_allowed(
        url,
        scheme["official_domains"]
    ):
        return

    visited.add(url)

    print(
        f"\n  PAGE [{depth}]: {url}"
    )

    response = fetch(url)

    if response is None:
        return

    if is_pdf(url, response):

        content = response.content

        # PDF cannot be fully validated here without
        # PyMuPDF. We require the filename/URL to
        # contain the scheme name or alias.
        pdf_name = (
            urlparse(url)
            .path
            .split("/")[-1]
        )

        if not scheme_matches(
            pdf_name,
            scheme
        ):
            print(
                "      SKIP PDF: scheme name not detected"
            )
            return

        freshness = freshness_score(
            pdf_name,
            response,
            url
        )

        if freshness["status"] == "HISTORICAL":
            print(
                "      SKIP: historical"
            )
            return

        save_pdf(
            response,
            scheme,
            state,
            url,
            None,
            freshness
        )

        return

    content_type = response.headers.get(
        "Content-Type",
        ""
    ).lower()

    if "html" not in content_type:
        return

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    title = extract_title(soup)

    text = normalize_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    # IMPORTANT:
    # Page must actually contain the target scheme.
    combined = (
        title
        + " "
        + text
    )

    if not scheme_matches(
        combined,
        scheme
    ):
        print(
            "      SKIP: scheme name not found"
        )
        return

    freshness = freshness_score(
        combined,
        response,
        url
    )

    print(
        f"      Scheme: {scheme['scheme_name']}"
    )

    print(
        f"      Freshness: "
        f"{freshness['status']}"
    )

    # Save current/undated HTML
    if freshness["status"] in [
        "CURRENT",
        "CURRENT_UNDATED"
    ]:
        save_html(
            soup,
            scheme,
            state,
            url,
            freshness
        )

    # Find PDFs
    for link in soup.find_all(
        "a",
        href=True
    ):

        href = link.get(
            "href",
            ""
        ).strip()

        if not href:
            continue

        child_url = urljoin(
            url,
            href
        )

        if not domain_allowed(
            child_url,
            scheme["official_domains"]
        ):
            continue

        anchor = normalize_text(
            link.get_text(
                " ",
                strip=True
            )
        )

        pdf_response = None

        if is_pdf(child_url):

            pdf_response = fetch(
                child_url
            )

            if pdf_response:

                # For PDFs we need a stronger
                # validation signal:
                # filename OR anchor should mention
                # scheme name/alias.
                pdf_hint = (
                    child_url
                    + " "
                    + anchor
                )

                if scheme_matches(
                    pdf_hint,
                    scheme
                ):

                    freshness = freshness_score(
                        pdf_hint,
                        pdf_response,
                        child_url
                    )

                    if freshness["status"] != "HISTORICAL":

                        save_pdf(
                            pdf_response,
                            scheme,
                            state,
                            child_url,
                            url,
                            freshness
                        )

                else:
                    print(
                        "      PDF skipped: "
                        "scheme not confirmed"
                    )

        else:

            if depth < MAX_DEPTH:
                queue.append(
                    (
                        child_url,
                        depth + 1
                    )
                )

    time.sleep(
        CRAWL_DELAY
    )


# ============================================================
# RUN ONE SCHEME
# ============================================================

def run_scheme(
    state,
    scheme
):

    print("\n" + "=" * 70)
    print(
        f"{state.upper()} :: "
        f"{scheme['scheme_name']}"
    )
    print("=" * 70)

    # Start with official government domains.
    #
    # We use the domain root as a controlled
    # discovery point.
    queue = []

    for domain in scheme[
        "official_domains"
    ]:

        if domain == "sspensions.ap.gov.in":
            queue.append(
                (
                    "https://sspensions.ap.gov.in/",
                    0
                )
            )

        elif domain == "handlooms.ap.gov.in":
            queue.append(
                (
                    "https://handlooms.ap.gov.in/stateschemes.html",
                    0
                )
            )

        elif domain == "telangana.gov.in":
            queue.append(
                (
                    "https://www.telangana.gov.in/government-initiatives/",
                    0
                )
            )

            queue.append(
                (
                    "https://www.telangana.gov.in/state-web-directory/",
                    0
                )
            )

        elif domain == "ap.gov.in":
            queue.append(
                (
                    "https://ap.gov.in/",
                    0
                )
            )

        elif domain == "cgg.gov.in":
            queue.append(
                (
                    "https://telanganaepass.cgg.gov.in/",
                    0
                )
            )

    visited = set()

    pages_processed = 0

    while queue:

        url, depth = queue.pop(0)

        if url in visited:
            continue

        if pages_processed >= MAX_PAGES_PER_DOMAIN:
            break

        process_page(
            url,
            state,
            scheme,
            visited,
            queue,
            depth
        )

        pages_processed += 1


# ============================================================
# MAIN
# ============================================================

def main():

    if not MANIFEST.exists():
        print(
            f"Manifest not found: {MANIFEST}"
        )
        return

    manifest = json.loads(
        MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    for state in [
        "telangana",
        "andhra_pradesh"
    ]:

        schemes = manifest.get(
            state,
            []
        )

        # Priority 1 first
        schemes = sorted(
            schemes,
            key=lambda x: (
                x["priority"],
                x["scheme_name"]
            )
        )

        for scheme in schemes:

            run_scheme(
                state,
                scheme
            )

    print("\n" + "=" * 70)
    print("STATE COLLECTION COMPLETED")
    print("=" * 70)

    print(
        f"Metadata: {METADATA_FILE}"
    )


if __name__ == "__main__":
    main()