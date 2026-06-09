from concurrent.futures import ThreadPoolExecutor

from ingestion.sources.base import BaseSource
from ingestion.utils.http import safe_get, normalize_doi
from ingestion.schemas.work import Work


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

    def search(self, query, limit=1000):
        url = "https://api.zbmath.org/v1/document/_search"
        page_size = 100
        page_count = (limit + page_size - 1) // page_size

        def fetch_page(page):
            params = {
                "search_string": query,
                "page": page,
                "results_per_page": page_size,
            }
            data = safe_get(url, params)
            return page, data.get("result", [])

        results_by_page = {}
        with ThreadPoolExecutor(max_workers=min(5, page_count)) as executor:
            for page, page_results in executor.map(fetch_page, range(page_count)):
                results_by_page[page] = page_results

        results = []
        for page in range(page_count):
            page_results = results_by_page.get(page, [])
            results.extend(page_results)
            if len(page_results) < page_size:
                break

        return results[:limit]

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
