import json
import re
import time
import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import requests

# -----------------------------
# Config
# -----------------------------
CROSSREF_MAILTO = "shreyas7140@gmail.com"  # put your email (Crossref recommends it)
CROSSREF_ROWS_PER_PAGE = 200  # max 1000, keep moderate
OPENALEX_PER_PAGE = 200       # max 200

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": f"math-metadata-harvester/1.0 (mailto:{CROSSREF_MAILTO})"})


# -----------------------------
# Helpers
# -----------------------------
def safe_get(url: str, params: Dict[str, Any], max_retries: int = 5, sleep_s: float = 1.0) -> Dict[str, Any]:
    """GET with basic retry/backoff."""
    for attempt in range(max_retries):
        try:
            resp = SESSION.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                # rate limited
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else (sleep_s * (2 ** attempt))
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(sleep_s * (2 ** attempt))
    raise RuntimeError("Unreachable")


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    d = doi.strip().lower()
    d = d.replace("https://doi.org/", "").replace("http://doi.org/", "").replace("doi:", "")
    return d.strip() or None


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def openalex_abstract_from_inverted_index(inv: Optional[Dict[str, List[int]]]) -> Optional[str]:
    """
    OpenAlex often provides abstract_inverted_index (word -> positions).
    Reconstruct into a string.
    """
    if not inv:
        return None
    # Build position -> word
    pos_to_word = {}
    for word, positions in inv.items():
        for p in positions:
            pos_to_word[p] = word
    if not pos_to_word:
        return None
    words = [pos_to_word[i] for i in range(max(pos_to_word.keys()) + 1) if i in pos_to_word]
    text = " ".join(words).strip()
    return text or None


def stable_fallback_id(payload: Dict[str, Any]) -> str:
    """
    When DOI is missing, create a stable ID from (title + year + first_author).
    This is a fallback and can collide; DOI is better.
    """
    title = (payload.get("title") or "").strip().lower()
    year = str(payload.get("year") or "")
    authors = payload.get("authors") or []
    first_author = ""
    if authors:
        first_author = (authors[0].get("name") or "").strip().lower()
    raw = f"{title}|{year}|{first_author}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


# -----------------------------
# Normalized schema
# -----------------------------
@dataclass
class WorkRecord:
    doi: Optional[str]
    title: Optional[str]
    abstract: Optional[str]
    authors: List[Dict[str, Any]]
    year: Optional[int]
    venue: Optional[str]
    issn: List[str]
    source_flags: Dict[str, bool]
    ids: Dict[str, Any]


# -----------------------------
# Crossref harvesting
# -----------------------------
def crossref_search_works(query: str, max_records: int = 1000, filter_str: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Crossref /works query. Use query for keywords.
    Optionally add filter_str like 'from-pub-date:2015-01-01,type:journal-article'
    """
    url = "https://api.crossref.org/works"
    results = []
    offset = 0

    while len(results) < max_records:
        rows = min(CROSSREF_ROWS_PER_PAGE, max_records - len(results))
        params = {
            "query": query,
            "rows": rows,
            "offset": offset,
            "mailto": CROSSREF_MAILTO,
        }
        if filter_str:
            params["filter"] = filter_str

        data = safe_get(url, params)
        items = data.get("message", {}).get("items", [])
        if not items:
            break

        results.extend(items)
        offset += rows

        # polite pause
        time.sleep(0.2)

    return results[:max_records]


def normalize_crossref_item(item: Dict[str, Any]) -> WorkRecord:
    doi = normalize_doi(item.get("DOI"))
    title = None
    if isinstance(item.get("title"), list) and item["title"]:
        title = item["title"][0]
    abstract = item.get("abstract")
    if abstract:
        abstract = strip_tags(abstract)

    # Authors
    authors = []
    for a in item.get("author", []) or []:
        given = a.get("given", "") or ""
        family = a.get("family", "") or ""
        name = (given + " " + family).strip() or a.get("name")
        authors.append({
            "name": name,
            "orcid": a.get("ORCID"),
            "affiliation": [aff.get("name") for aff in (a.get("affiliation") or []) if aff.get("name")]
        })

    year = None
    # Prefer published-print, then published-online, then created
    for key in ["published-print", "published-online", "created", "issued"]:
        parts = item.get(key, {}).get("date-parts")
        if parts and parts[0] and parts[0][0]:
            year = int(parts[0][0])
            break

    venue = None
    if isinstance(item.get("container-title"), list) and item["container-title"]:
        venue = item["container-title"][0]

    issn = item.get("ISSN") or []
    issn = [s.strip() for s in issn if s and isinstance(s, str)]

    return WorkRecord(
        doi=doi,
        title=title,
        abstract=abstract,
        authors=authors,
        year=year,
        venue=venue,
        issn=issn,
        source_flags={"crossref": True, "openalex": False},
        ids={"crossref": {"member": item.get("member"), "prefix": item.get("prefix")}}
    )


# -----------------------------
# OpenAlex harvesting
# -----------------------------
def openalex_search_works(query: str, max_records: int = 1000, from_year: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    OpenAlex /works search.
    """
    url = "https://api.openalex.org/works"
    results = []
    cursor = "*"

    while len(results) < max_records:
        per_page = min(OPENALEX_PER_PAGE, max_records - len(results))
        params = {
            "search": query,
            "per-page": per_page,
            "cursor": cursor,
        }
        if from_year:
            params["filter"] = f"from_publication_date:{from_year}-01-01"

        data = safe_get(url, params)
        items = data.get("results", [])
        if not items:
            break

        results.extend(items)
        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor:
            break

        time.sleep(0.2)

    return results[:max_records]


def normalize_openalex_item(item: Dict[str, Any]) -> WorkRecord:
    doi = normalize_doi(item.get("doi"))
    title = item.get("title")
    abstract = item.get("abstract")
    if not abstract:
        abstract = openalex_abstract_from_inverted_index(item.get("abstract_inverted_index"))

    authors = []
    for au in item.get("authorships", []) or []:
        a = au.get("author", {}) or {}
        authors.append({
            "name": a.get("display_name"),
            "orcid": a.get("orcid"),
            "affiliation": [inst.get("display_name") for inst in (au.get("institutions") or []) if inst.get("display_name")]
        })

    year = item.get("publication_year")
    venue = None
    host = item.get("primary_location", {}).get("source")
    if host:
        venue = host.get("display_name")

    issn = []
    if host and host.get("issn"):
        issn = host.get("issn") or []
    issn = [s.strip() for s in issn if s and isinstance(s, str)]

    return WorkRecord(
        doi=doi,
        title=title,
        abstract=abstract,
        authors=authors,
        year=int(year) if year else None,
        venue=venue,
        issn=issn,
        source_flags={"crossref": False, "openalex": True},
        ids={"openalex": {"id": item.get("id"), "type": item.get("type")}}
    )


# -----------------------------
# Merge logic
# -----------------------------
def merge_records(a: WorkRecord, b: WorkRecord) -> WorkRecord:
    """
    Merge two WorkRecords, preferring non-null fields and unioning lists/flags/ids.
    DOI should match or one may be None.
    """
    doi = a.doi or b.doi
    title = a.title or b.title
    abstract = a.abstract or b.abstract

    # Merge authors (very naive: keep the longer list)
    authors = a.authors if len(a.authors) >= len(b.authors) else b.authors

    year = a.year or b.year
    venue = a.venue or b.venue
    issn = sorted(set((a.issn or []) + (b.issn or [])))

    source_flags = {
        "crossref": a.source_flags.get("crossref", False) or b.source_flags.get("crossref", False),
        "openalex": a.source_flags.get("openalex", False) or b.source_flags.get("openalex", False),
    }

    ids = {}
    ids.update(a.ids or {})
    for k, v in (b.ids or {}).items():
        if k not in ids:
            ids[k] = v
        else:
            # merge dicts shallowly
            if isinstance(ids[k], dict) and isinstance(v, dict):
                ids[k] = {**ids[k], **v}

    return WorkRecord(doi, title, abstract, authors, year, venue, issn, source_flags, ids)


def upsert_work(store: Dict[str, WorkRecord], rec: WorkRecord) -> None:
    key = rec.doi or f"no_doi:{stable_fallback_id(asdict(rec))}"
    if key in store:
        store[key] = merge_records(store[key], rec)
    else:
        store[key] = rec


# -----------------------------
# Output + stats
# -----------------------------
def write_jsonl(path: str, records: List[WorkRecord]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def print_stats(records: List[WorkRecord]) -> None:
    n = len(records)
    with_abs = sum(1 for r in records if r.abstract and r.abstract.strip())
    with_doi = sum(1 for r in records if r.doi)
    crossref_only = sum(1 for r in records if r.source_flags["crossref"] and not r.source_flags["openalex"])
    openalex_only = sum(1 for r in records if r.source_flags["openalex"] and not r.source_flags["crossref"])
    both = sum(1 for r in records if r.source_flags["crossref"] and r.source_flags["openalex"])
    venues = len(set(r.venue for r in records if r.venue))
    issns = len(set(s for r in records for s in (r.issn or [])))

    print(f"Total works: {n}")
    print(f"With DOI: {with_doi} ({with_doi/n:.1%})")
    print(f"With abstract: {with_abs} ({with_abs/n:.1%})")
    print(f"Source coverage: crossref_only={crossref_only}, openalex_only={openalex_only}, both={both}")
    print(f"Unique venues: {venues}")
    print(f"Unique ISSNs: {issns}")


# -----------------------------
# Main example run
# -----------------------------
if __name__ == "__main__":
    # Example query. Replace with your "math domain" seed, e.g. "algebraic geometry", "spectral theory", etc.
    # QUERY = "algebraic topology"
    # MAX = 500
    QUERY = "algebra"
    MAX = 100

    # Crossref: try to bias toward journal articles, recent-ish
    crossref_filter = "type:journal-article,from-pub-date:2010-01-01"
    cross_items = crossref_search_works(query=QUERY, max_records=MAX, filter_str=crossref_filter)
    openalex_items = openalex_search_works(query=QUERY, max_records=MAX, from_year=2010)

    store: Dict[str, WorkRecord] = {}

    for it in cross_items:
        upsert_work(store, normalize_crossref_item(it))

    for it in openalex_items:
        upsert_work(store, normalize_openalex_item(it))

    merged = list(store.values())
    write_jsonl("works.jsonl", merged)
    print_stats(merged)
    print("Wrote works.jsonl")
