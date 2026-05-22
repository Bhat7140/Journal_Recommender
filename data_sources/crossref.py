from data_sources.base import BaseSource
from utils.http import safe_get, normalize_doi
from utils.issn import normalize_issn_list
from models.work import Work

class CrossrefSource(BaseSource):

    def __init__(self, work_filters=None):
        # work_filters: Crossref /works filters for source searches, e.g. has-abstract:1.
        self.work_filters = work_filters or []

    def search(self, query, limit=1000):
        url = "https://api.crossref.org/works"
        params = {"query": query, "rows": limit}

        if self.work_filters:
            # Crossref filters do not isolate physics/math well, but they improve metadata quality.
            params["filter"] = ",".join(self.work_filters)

        data = safe_get(url, params)
        return data.get("message", {}).get("items", [])

    def get_by_doi(self, doi):
        url = f"https://api.crossref.org/works/{doi}"
        try:
            return safe_get(url, {}).get("message")
        except:
            return None

    def normalize(self, item):
        # -----------------------------
        # Title
        # -----------------------------
        title = item.get("title", [None])[0]

        # -----------------------------
        # Authors
        # -----------------------------
        authors = []
        for a in item.get("author", []):
            name = f"{a.get('given','')} {a.get('family','')}".strip()
            authors.append(name)

        # -----------------------------
        # Year extraction
        # -----------------------------
        year = None
        parts = item.get("issued", {}).get("date-parts")
        if parts and parts[0]:
            year = parts[0][0]

        # -----------------------------
        # ISSN extraction
        # -----------------------------
        issn = normalize_issn_list(item.get("ISSN") or [])

        # -----------------------------
        # Venue
        # -----------------------------
        venue = (item.get("container-title") or [None])[0]

        # -----------------------------
        # Return normalized Work object
        # -----------------------------
        return Work(
            doi=normalize_doi(item.get("DOI")),
            title=title,
            abstract=item.get("abstract"),
            year=year,
            authors=authors,
            venue=venue,
            subjects=[],      # Crossref does not provide MSC
            issn=issn,
            source={"crossref": True},
            journal_name=venue if issn else None,
        )
