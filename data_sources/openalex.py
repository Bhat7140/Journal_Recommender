from concurrent.futures import ThreadPoolExecutor

from data_sources.base import BaseSource
from utils.http import safe_get, normalize_doi
from utils.issn import normalize_issn_list
from models.work import Work

OPENALEX_BASE_URL = "https://api.openalex.org"

def reconstruct_abstract(inv):
    if not inv:
        return None
    pos = {}
    for word, positions in inv.items():
        for p in positions:
            pos[p] = word
    return " ".join(pos[i] for i in sorted(pos))


def safe_dict(value):
    return value if isinstance(value, dict) else {}


class OpenAlexSource(BaseSource):

    def __init__(self, topic_field_names=None, work_filters=None):
        # topic_field_names: human-readable OpenAlex fields, e.g. "Physics and Astronomy".
        self.topic_field_names = topic_field_names or []
        # work_filters: direct OpenAlex /works filters, e.g. has_abstract:true,type:article.
        self.work_filters = work_filters or []
        # _topic_field_ids: cached resolved field IDs so we only call /fields once per source.
        self._topic_field_ids = None

    def resolve_topic_field_ids(self):
        if self._topic_field_ids is not None:
            return self._topic_field_ids

        field_ids = []

        for field_name in self.topic_field_names:
            # OpenAlex /works filters need IDs, so resolve "Physics and Astronomy" via /fields search.
            data = safe_get(f"{OPENALEX_BASE_URL}/fields", {"search": field_name, "per-page": 5}) or {}
            results = data.get("results", [])

            exact = next(
                (
                    item
                    for item in results
                    if isinstance(item, dict)
                    if item.get("display_name", "").lower() == field_name.lower()
                ),
                None,
            )
            selected = exact or (results[0] if results else None)

            if selected and selected.get("id"):
                field_ids.append(str(selected["id"]).replace("https://openalex.org/fields/", ""))

        self._topic_field_ids = field_ids
        return field_ids

    def build_filter_param(self):
        filters = list(self.work_filters)
        field_ids = self.resolve_topic_field_ids()

        if field_ids:
            # topics.field.id isolates records to the selected OpenAlex discipline field.
            filters.append(f"topics.field.id:{'|'.join(field_ids)}")

        return ",".join(filters) if filters else None

    def search(self, query, limit=1000):
        url = f"{OPENALEX_BASE_URL}/works"
        filter_param = self.build_filter_param()
        page_size = min(200, limit)
        page_count = (limit + page_size - 1) // page_size

        def fetch_page(page):
            params = {
                "search": query,
                "per-page": page_size,
                "page": page,
            }

            if filter_param:
                params["filter"] = filter_param

            data = safe_get(url, params) or {}
            return page, data.get("results", [])

        results_by_page = {}
        with ThreadPoolExecutor(max_workers=min(5, page_count)) as executor:
            for page, page_results in executor.map(fetch_page, range(1, page_count + 1)):
                results_by_page[page] = page_results

        results = []
        for page in range(1, page_count + 1):
            page_results = results_by_page.get(page, [])
            results.extend(page_results)
            if len(page_results) < page_size:
                break

        return results[:limit]

    def get_by_doi(self, doi):
        url = f"{OPENALEX_BASE_URL}/works"
        params = {"filter": f"doi:{doi}"}
        data = safe_get(url, params) or {}
        res = data.get("results", [])
        return res[0] if res else None

    def normalize(self, item):
        item = safe_dict(item)

        # -----------------------------
        # Abstract reconstruction
        # -----------------------------
        abstract = reconstruct_abstract(item.get("abstract_inverted_index"))

        # -----------------------------
        # Authors
        # -----------------------------
        authors = []
        for authorship in item.get("authorships") or []:
            author = safe_dict(safe_dict(authorship).get("author"))
            name = author.get("display_name")
            if name:
                authors.append(name)

        # -----------------------------
        # Venue + ISSN extraction
        # -----------------------------
        primary_location = safe_dict(item.get("primary_location"))
        host = safe_dict(primary_location.get("source"))

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
        issn = normalize_issn_list(issn)

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
            source={"openalex": True},
            journal_name=venue if issn else None,
        )
