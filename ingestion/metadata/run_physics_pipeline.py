import json
from pathlib import Path

from configs.physics_keyword_config import (
    ARXIV_PHYSICS_CATEGORIES,
    CROSSREF_PHYSICS_WORK_FILTERS,
    OPENALEX_PHYSICS_FIELD_NAMES,
    OPENALEX_PHYSICS_WORK_FILTERS,
    PHYSICS_QUERIES,
)
from ingestion.sources.arxiv import ArxivSource
from ingestion.sources.crossref import CrossrefSource
from ingestion.sources.openalex import OpenAlexSource
from ingestion.metadata.core_pipeline import Pipeline, merge
from ingestion.metadata.metadata_cleanup import require_issn_and_journal_names

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = BASE_DIR / "output" / "metadata" / "physics"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record.__dict__, ensure_ascii=False) + "\n")


def dedupe_key(record):
    return record.doi or f"{(record.title or 'untitled').strip().lower()}{record.year or ''}"


def merge_records(records):
    unique = {}

    for record in records:
        key = dedupe_key(record)
        if key in unique:
            unique[key] = merge(unique[key], record)
        else:
            unique[key] = record

    return list(unique.values())


def run():
    # OpenAlex base search is restricted to Physics and Astronomy + article records with abstracts.
    oa = OpenAlexSource(
        topic_field_names=OPENALEX_PHYSICS_FIELD_NAMES,
        work_filters=OPENALEX_PHYSICS_WORK_FILTERS,
    )
    # Crossref filters apply only when Crossref is used for search; DOI enrichment still uses DOI lookup.
    cr = CrossrefSource(work_filters=CROSSREF_PHYSICS_WORK_FILTERS)
    # arXiv category searches already isolate physics using explicit cat:<category> queries.
    arxiv = ArxivSource()

    # Slow mode: enriching every OpenAlex result with arXiv and every arXiv result with OpenAlex
    # caused too many per-paper API calls, so those enrichers are paused for now.
    # openalex_pipeline = Pipeline(primary_source=oa, enrich_sources=[cr, arxiv])
    # arxiv_pipeline = Pipeline(primary_source=arxiv, enrich_sources=[cr, oa])
    openalex_pipeline = Pipeline(
        primary_source=oa,
        enrich_sources=[cr],
        max_workers=32,
        stop_enrichment_when_issn=True,
    )
    arxiv_pipeline = Pipeline(
        primary_source=arxiv,
        enrich_sources=[cr],
        max_workers=32,
        stop_enrichment_when_issn=True,
    )

    all_results = []

    for query in PHYSICS_QUERIES:
        print(f"[PHYSICS:OPENALEX] {query}")
        openalex_pipeline.store = {}
        all_results.extend(openalex_pipeline.run(query))

    for category in ARXIV_PHYSICS_CATEGORIES:
        print(f"[PHYSICS:ARXIV] {category}")
        arxiv_pipeline.store = {}
        all_results.extend(arxiv_pipeline.run(f"cat:{category}"))

    results = merge_records(all_results)

    write_jsonl(OUTPUT_DIR / "raw.jsonl", results)

    clean = [
        record
        for record in require_issn_and_journal_names(results)
        if record.abstract and len(record.abstract) > 100
    ]
    write_jsonl(OUTPUT_DIR / "clean.jsonl", clean)

    print(f"[PHYSICS] Raw: {len(results)} | Clean with ISSN: {len(clean)}")


if __name__ == "__main__":
    run()
