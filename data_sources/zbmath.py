from data_sources.base import BaseSource
from utils.http import safe_get, normalize_doi
from models.work import Work

class ZBMathSource(BaseSource):

    def search(self, query, limit=100):
        url = "https://api.zbmath.org/v1/document/_search"
        params = {"q": query, "size": limit}
        data = safe_get(url, params)
        return data.get("hits", {}).get("hits", [])

    def get_by_doi(self, doi):
        return None

    def normalize(self, item):
        src = item["_source"]

        return Work(
            doi=normalize_doi(src.get("doi")),
            title=src.get("title"),
            abstract=src.get("abstract"),
            year=src.get("year"),
            authors=[a.get("name") for a in src.get("authors", [])],
            venue=src.get("source"),
            subjects=src.get("classification", []),
            issn=src.get("issn", []) or [],
            source={"zbmath": True}
        )