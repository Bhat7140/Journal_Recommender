from typing import Dict
from models.work import Work

DEFAULT_MAX_RESULTS = 5000


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

    def __init__(
            self,
            primary_source,
            enrich_sources,
    ):
        self.primary = primary_source
        self.enrich_sources = enrich_sources
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

    def run(self, query):

        print(f"\nRunning pipeline for query: {query}")

        # -----------------------------------
        # 1. Retrieve records
        # -----------------------------------

        items = self.primary.search(query)

        print(f"Retrieved {len(items)} records")

        # -----------------------------------
        # 2. Optional limiter
        # -----------------------------------

        if DEFAULT_MAX_RESULTS:

            items = items[:DEFAULT_MAX_RESULTS]

            print(
            f"Limited to {len(items)} records "
            f"(DEFAULT_MAX_RESULTS)"
            )

        else:

            print("No limiter applied")

        # -----------------------------------
        # 3. Normalize + enrich
        # -----------------------------------

        for idx, item in enumerate(items, start=1):

            print(f"\nProcessing {idx}/{len(items)}")

            rec = self.primary.normalize(item)

            self.upsert(rec)

            if rec.doi:

                for src in self.enrich_sources:

                    try:

                        enriched = src.get_by_doi(rec.doi)

                        if enriched:

                            normalized = src.normalize(enriched)

                            self.upsert(normalized)

                            print(
                                f"Enriched from "
                                f"{src.__class__.__name__}"
                            )

                    except Exception as e:

                        print(
                            f"Failed enrichment from "
                            f"{src.__class__.__name__}: {e}"
                        )

        print("\nPipeline complete")
        print(f"Final unique records: {len(self.store)}")

        return list(self.store.values())