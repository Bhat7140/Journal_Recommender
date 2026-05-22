from concurrent.futures import ThreadPoolExecutor, as_completed
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
        source={**a.source, **b.source},
        journal_name=a.journal_name or b.journal_name,
    )


class Pipeline:

    def __init__(
            self,
            primary_source,
            enrich_sources,
            max_workers=12,
            stop_enrichment_when_issn=False,
    ):
        self.primary = primary_source
        self.enrich_sources = enrich_sources
        self.max_workers = max_workers
        self.stop_enrichment_when_issn = stop_enrichment_when_issn
        self.store: Dict[str, Work] = {}

    def upsert(self, record: Work):

        key = (
                record.doi
                or (
                        record.title.strip().lower()
                        + str(record.year)
                )
        )

        if key in self.store:
            self.store[key] = merge(self.store[key], record)
        else:
            self.store[key] = record

    def process_item(self, item):
        rec = self.primary.normalize(item)
        current = rec

        if rec.doi:
            for src in self.enrich_sources:
                try:
                    enriched = src.get_by_doi(rec.doi)

                    if enriched:
                        current = merge(current, src.normalize(enriched))

                        # For the metadata workflows, Crossref/OpenAlex enrichment is
                        # primarily needed to get ISSN-backed journal identity. Once we
                        # have that, avoid another slow DOI lookup unless explicitly needed.
                        if self.stop_enrichment_when_issn and current.issn:
                            break

                except Exception as e:
                    print(
                        f"Failed enrichment from "
                        f"{src.__class__.__name__}: {e}"
                    )

        return [current]

    def run(self, query):

        print(f"\nRunning pipeline for query: {query}")

        # -----------------------------------
        # 1. Retrieve records
        # -----------------------------------

        items = self.primary.search(query)

        print(f"Retrieved {len(items)} records")

        # -----------------------------------
        # 2. Normalize + enrich
        # -----------------------------------

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.process_item, item): idx
                for idx, item in enumerate(items, start=1)
            }

            for completed, future in enumerate(as_completed(futures), start=1):
                idx = futures[future]
                try:
                    for record in future.result():
                        self.upsert(record)
                except Exception as e:
                    print(f"Failed processing item {idx}: {e}")

                if completed % 25 == 0 or completed == len(items):
                    print(f"Processed {completed}/{len(items)} records")

        print("\nPipeline complete")
        print(f"Final unique records: {len(self.store)}")

        return list(self.store.values())
