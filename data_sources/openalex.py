from data_sources.base import BaseSource
from utils.http import safe_get, normalize_doi
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
            data = safe_get(f"{OPENALEX_BASE_URL}/fields", {"search": field_name, "per-page": 5})
            results = data.get("results", [])

            exact = next(
                (
                    item
                    for item in results
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

    def search(self, query, limit=100):
        url = f"{OPENALEX_BASE_URL}/works"
        params = {"search": query, "per-page": limit}
        filter_param = self.build_filter_param()

        if filter_param:
            params["filter"] = filter_param

        data = safe_get(url, params)
        return data.get("results", [])

    def get_by_doi(self, doi):
        url = f"{OPENALEX_BASE_URL}/works"
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
