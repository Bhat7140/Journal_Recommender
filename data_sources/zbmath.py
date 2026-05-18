from data_sources.base import BaseSource
from utils.http import safe_get, normalize_doi
from models.work import Work


def first_review_text(item):
    for contribution in item.get("editorial_contributions", []):
        text = contribution.get("text")
        if text:
            return text
    return None


def parse_year(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def extract_doi(item):
    doi = normalize_doi(item.get("doi"))
    if doi:
        return doi

    for link in item.get("links", []):
        if link.get("type") == "doi":
            return normalize_doi(link.get("identifier") or link.get("url"))

    return None


class ZBMathSource(BaseSource):

    def search(self, query, limit=100):
        url = "https://api.zbmath.org/v1/document/_search"
        params = {"search_string": query, "size": limit}
        data = safe_get(url, params)
        return data.get("result", [])

    def get_by_doi(self, doi):
        return None

    def normalize(self, item):

        title = item.get("title") or {}
        contributors = item.get("contributors") or {}
        source = item.get("source") or {}

        return Work(
            doi=extract_doi(item),
            title=title.get("title") or "untitled",
            abstract=first_review_text(item),
            year=parse_year(item.get("year")),
            authors=[
                author.get("name")
                for author in contributors.get("authors", [])
                if author.get("name")
            ],
            venue=source.get("source"),
            subjects=[
                subject.get("code")
                for subject in item.get("msc", [])
                if subject.get("code")
            ],
            issn=[],
            source={"zbmath": True}
        )
