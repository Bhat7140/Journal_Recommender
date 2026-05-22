from utils.http import safe_get
from utils.issn import normalize_issn


class JournalNameResolver:
    def __init__(self):
        self.cache = {}

    def resolve(self, issn_values):
        for value in issn_values or []:
            issn = normalize_issn(value)
            if not issn:
                continue

            if issn not in self.cache:
                self.cache[issn] = self._lookup(issn)

            if self.cache[issn]:
                return self.cache[issn]

        return None

    def _lookup(self, issn):
        name = self._lookup_crossref(issn)
        if name:
            return name

        return self._lookup_openalex(issn)

    def _lookup_crossref(self, issn):
        try:
            data = safe_get(f"https://api.crossref.org/journals/{issn}", {})
        except Exception:
            return None

        title = data.get("message", {}).get("title")
        if title:
            return " ".join(str(title).split())

        return None

    def _lookup_openalex(self, issn):
        try:
            data = safe_get(
                "https://api.openalex.org/sources",
                {"filter": f"issn:{issn}", "per-page": 1},
            )
        except Exception:
            return None

        results = data.get("results") or []
        if not results:
            return None

        name = results[0].get("display_name")
        if name:
            return " ".join(str(name).split())

        return None
