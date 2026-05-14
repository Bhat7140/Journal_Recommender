from typing import Dict
from models.work import Work

def merge(a: Work, b: Work) -> Work:
    return Work(
        doi=a.doi or b.doi,
        title=a.title or b.title,
        abstract=a.abstract or b.abstract,
        year=a.year or b.year,
        authors=a.authors if len(a.authors) >= len(b.authors) else b.authors,
        venue=a.venue or b.venue,
        subjects=a.subjects or b.subjects,
        issn=list(set((a.issn or []) + (b.issn or []))),
        source={**a.source, **b.source}
    )

class Pipeline:

    def __init__(self, primary_source, enrich_sources):
        self.primary = primary_source
        self.enrich_sources = enrich_sources
        self.store: Dict[str, Work] = {}

    def upsert(self, record: Work):
        key = record.doi or (record.title + str(record.year))
        self.store[key] = merge(self.store[key], record) if key in self.store else record

    def run(self, query):
        items = self.primary.search(query)

        for item in items:
            rec = self.primary.normalize(item)
            self.upsert(rec)

            if rec.doi:
                for src in self.enrich_sources:
                    enriched = src.get_by_doi(rec.doi)
                    if enriched:
                        self.upsert(src.normalize(enriched))

        return list(self.store.values())