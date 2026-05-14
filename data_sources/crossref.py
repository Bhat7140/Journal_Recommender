from data_sources.base import BaseSource
from utils.http import safe_get, normalize_doi
from models.work import Work

class CrossrefSource(BaseSource):

    def search(self, query, limit=100):
        url = "https://api.crossref.org/works"
        params = {"query": query, "rows": limit}
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
        issn = item.get("ISSN") or []
        issn = [s.strip() for s in issn if isinstance(s, str)]

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
            source={"crossref": True}
        )