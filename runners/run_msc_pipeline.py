import json
from pathlib import Path

from data_sources.zbmath import ZBMathSource
from data_sources.crossref import CrossrefSource
from data_sources.openalex import OpenAlexSource
from pipelines.core_pipeline import Pipeline
from configs.math_msc_config import MSC_CODES

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = BASE_DIR / "output" / "msc"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.__dict__, ensure_ascii=False) + "\n")

def run():
    zb, cr, oa = ZBMathSource(), CrossrefSource(), OpenAlexSource()
    pipeline = Pipeline(primary_source=zb, enrich_sources=[cr, oa])

    all_results = []

    for code in MSC_CODES:
        print(f"[MSC] {code}")
        pipeline.store = {}
        all_results.extend(pipeline.run(code))

    unique = { (r.doi or (r.title + str(r.year))): r for r in all_results }
    results = list(unique.values())

    write_jsonl(OUTPUT_DIR / "raw.jsonl", results)

    clean = [r for r in results if r.abstract and len(r.abstract) > 100]
    write_jsonl(OUTPUT_DIR / "clean.jsonl", clean)

    print(f"[MSC] Raw: {len(results)} | Clean: {len(clean)}")

if __name__ == "__main__":
    run()
