from data_sources.base import BaseSource
from utils.http import safe_get, normalize_doi
from models.work import Work

def reconstruct_abstract(inv):
    if not inv:
        return None
    pos = {}
    for word, positions in inv.items():
        for p in positions:
            pos[p] = word
    return " ".join(pos[i] for i in sorted(pos))


class OpenAlexSource(BaseSource):

    def search(self, query, limit=100):
        url = "https://api.openalex.org/works"
        params = {"search": query, "per-page": limit}
        data = safe_get(url, params)
        return data.get("results", [])

    def get_by_doi(self, doi):
        url = "https://api.openalex.org/works"
        params = {"filter": f"doi:{doi}"}
        data = safe_get(url, params)
        res = data.get("results", [])
        return res[0] if res else None

    def normalize(self, item):
        # -----------------------------
        # Abstract reconstruction
        # -----------------------------
        abstract = reconstruct_abstract(item.get("abstract_inverted_index"))

        # -----------------------------
        # Authors
        # -----------------------------
        authors = [
            a["author"]["display_name"]
            for a in item.get("authorships", [])
        ]

        # -----------------------------
        # Venue + ISSN extraction
        # -----------------------------
        host = item.get("primary_location", {}).get("source")

        venue = None
        issn = []

        if host:
            venue = host.get("display_name")

            # OpenAlex can store ISSN in multiple forms
            if host.get("issn"):
                issn = host.get("issn")

            # fallback
            elif host.get("issn_l"):
                issn = [host.get("issn_l")]

        # Clean ISSN list
        issn = [s.strip() for s in issn if isinstance(s, str)]

        # -----------------------------
        # Return Work object
        # -----------------------------
        return Work(
            doi=normalize_doi(item.get("doi")),
            title=item.get("title"),
            abstract=abstract,
            year=item.get("publication_year"),
            authors=authors,
            venue=venue,
            subjects=[],
            issn=issn,
            source={"openalex": True}
        )