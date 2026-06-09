# Journal Recommender

This project builds a math-focused journal recommendation pipeline. It collects
publication metadata, keeps only records that can be mapped back to journals by
ISSN, creates transformer embeddings, indexes the records into OpenSearch, and
supports keyword, vector, and hybrid retrieval.

The main production-oriented workflow is the MSC workflow, because it uses
Mathematics Subject Classification codes and descriptions to represent the
mathematical area of a manuscript.


## What The Project Does

At a high level, the project does this:

```text
metadata APIs
    -> normalized Work records
    -> ISSN/journal cleanup
    -> JSONL metadata
    -> transformer embeddings
    -> OpenSearch vector index
    -> search / hybrid search / evaluation / previews
```

The final recommender can take a manuscript-like input:

```text
Title
Abstract
```

embed it with the same transformer used for indexed metadata, search the MSC
OpenSearch index, and return ranked journal/paper evidence with:

```text
hybrid score
title
year
authors
journal_name
venue
ISSN
DOI
abstract
```


## Repository Structure

```text
configs/
  embedding_config.py          Embedding model, scenario paths, output roots
  opensearch_config.py         OpenSearch connection, index names, paths
  math_msc_config.py           MSC queries used for MSC metadata collection
  math_keyword_config.py       Keyword queries used for no-MSC collection
  msc_code_descriptions.py     Top-level MSC code descriptions

ingestion/
  sources/
    zbmath.py                  zbMATH metadata source
    crossref.py                Crossref metadata/enrichment source
    openalex.py                OpenAlex metadata/enrichment source
    arxiv.py                   arXiv metadata source
    journal_lookup.py          ISSN -> journal name resolver
  schemas/
    work.py                    Normalized Work metadata schema
  metadata/
    core_pipeline.py           Metadata retrieval, normalization, enrichment
    run_msc_pipeline.py        Collect MSC metadata
    run_no_msc_pipeline.py     Collect no-MSC metadata
    run_physics_pipeline.py    Collect physics metadata
    metadata_cleanup.py        ISSN/journal cleanup
  embeddings/
    create_msc_embeddings.py
    create_no_msc_embeddings.py
    create_physics_embeddings.py
    embedding_common.py
  indexing/
    index_msc_opensearch.py
    index_no_msc_opensearch.py
  utils/
    http.py                    Retry-safe HTTP helpers for ingestion sources
    issn.py                    ISSN normalization helpers

core/
  search/
    opensearch_backend.py      OpenSearch indexing/search/hybrid helpers
    search_msc_opensearch.py
    search_no_msc_opensearch.py
    run_dummy_user_hybrid_search.py
  evaluation/
    evaluate_msc_hybrid_opensearch.py
    evaluate_no_msc_hybrid_opensearch.py
    visualize_msc_hybrid_evaluation.py
    visualize_no_msc_hybrid_evaluation.py
    export_msc_opensearch_table.py
    export_no_msc_opensearch_table.py

ui/
  app.py                       UI placeholder

output/
  metadata/                    Raw and clean metadata JSONL files
  embeddings/                  works.jsonl, embeddings.npy, metadata
  opensearch_preview/          HTML/CSV index previews
  opensearch_evaluation*/      Evaluation CSVs and reports
  user_queries/                Dummy user search result JSON
```


## Core Data Model

All sources are normalized into the `Work` dataclass:

```python
class Work:
    doi: Optional[str]
    title: Optional[str]
    abstract: Optional[str]
    year: Optional[int]
    authors: List[str]
    venue: Optional[str]
    subjects: List[str]
    issn: List[str]
    source: Dict[str, bool]
    journal_name: Optional[str] = None
```

Important fields:

- `subjects`: MSC codes for math records when available.
- `issn`: stable journal identifier. Clean metadata requires this.
- `journal_name`: resolved from ISSN using Crossref/OpenAlex where possible.
- `venue`: source/citation string. It may be a journal name, but can also be a
  longer citation-like string.


## Why ISSN Is Required

This is a journal recommender, so every record in the final clean/indexed
dataset should map back to a real journal. ISSN is the stable identifier used
for that.

Records without ISSN are excluded from clean metadata because they cannot be
reliably mapped back to a journal. This removes books, proceedings, chapters,
older records, and noisy citation-only records.

The project keeps:

```text
raw.jsonl    all collected records for audit/debugging
clean.jsonl  records with usable abstract and ISSN
```


## Metadata Collection

### MSC Metadata

MSC collection is the main math-domain workflow.

```powershell
python -m ingestion.metadata.run_msc_pipeline
```

This uses:

- zbMATH as primary source
- Crossref and OpenAlex for DOI enrichment
- ISSN/journal cleanup

Outputs:

```text
output/metadata/msc/raw.jsonl
output/metadata/msc/clean.jsonl
```

The clean MSC file is ISSN-filtered. In the current run it contained:

```text
10920 records
0 missing ISSN
```


### no-MSC Metadata

```powershell
python -m ingestion.metadata.run_no_msc_pipeline
```

Outputs:

```text
output/metadata/no_msc/raw.jsonl
output/metadata/no_msc/clean.jsonl
```


## Metadata Collection Performance

The metadata pipeline uses concurrency because API collection is slow:

- source pagination is parallelized for zbMATH and OpenAlex
- DOI enrichment is parallelized with `ThreadPoolExecutor`
- ISSN journal-name lookup resolves unique ISSNs in parallel
- HTTP sessions are thread-local

The main runner settings currently use:

```python
max_workers=32
stop_enrichment_when_issn=True
```

`stop_enrichment_when_issn=True` means that once enrichment finds ISSN-backed
journal identity, it skips remaining enrichment calls for that record. This
saves many network requests.

If APIs rate-limit or DNS/network errors appear, reduce `max_workers` in the
metadata runner to `16`.


## Embeddings

The project uses:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Embeddings are normalized:

```python
normalize_embeddings=True
```


### MSC Embeddings

Command:

```powershell
python -m ingestion.embeddings.create_msc_embeddings
```

Input:

```text
output/metadata/msc/clean.jsonl
```

Output:

```text
output/embeddings/msc_clean/works.jsonl
output/embeddings/msc_clean/embeddings.npy
output/embeddings/msc_clean/embedding_metadata.json
```

MSC embedding text contains:

```text
Title
MSC codes
MSC descriptions
Venue
Abstract
```

It intentionally does not include `journal_name` in the dense embedding text.
This avoids leaking journal identity into the semantic vector. `journal_name`
is still stored in OpenSearch metadata and can be used for display, filtering,
BM25, and journal aggregation.


### no-MSC Embeddings

Command:

```powershell
python -m ingestion.embeddings.create_no_msc_embeddings
```

Input:

```text
output/metadata/no_msc/clean.jsonl
```

Output:

```text
output/embeddings/no_msc_clean/
```


## OpenSearch

OpenSearch stores:

- metadata fields
- ISSN/journal fields
- embedding vectors
- source flags

The vector field is defined as:

```text
knn_vector
```

with cosine similarity through OpenSearch k-NN.


### Index MSC

```powershell
python -m ingestion.indexing.index_msc_opensearch --recreate
```

Use `--recreate` whenever metadata or embeddings have changed. Without it,
OpenSearch upserts new documents but does not remove old documents that are no
longer present in the current dataset.

Current MSC index:

```text
index name: journal_recommender_msc
records:    10920
dimension:  384
```


### Index no-MSC

```powershell
python -m ingestion.indexing.index_no_msc_opensearch --recreate
```


## Search Modes

The project supports three retrieval modes.


### Keyword Search

BM25 search over text/metadata fields.

For MSC:

```text
title^3
subjects^3
abstract
journal_name^2
venue^2
authors
```


### Vector Search

Dense retrieval using the query embedding against the stored `knn_vector`
field.

This was the strongest method in MSC evaluation because MSC embeddings contain
MSC codes and descriptions, and the evaluation rewards MSC similarity.


### Hybrid Search

Hybrid search combines:

- BM25 branch
- dense vector branch

OpenSearch uses a search pipeline with score normalization:

```text
normalization: min_max
combination: arithmetic_mean
```

Evaluated hybrid weights:

```text
hybrid_50_50 = 0.5 BM25 / 0.5 dense
hybrid_70_30 = 0.7 BM25 / 0.3 dense
```


## CLI Search

### MSC Search

```powershell
python -m core.search.search_msc_opensearch --mode hybrid --create-hybrid-pipeline --title "Lie algebra cohomology" --subjects "17B56 20G05" --abstract "We study representations and quantum group cohomology."
```

### no-MSC Search

```powershell
python -m core.search.search_no_msc_opensearch --mode hybrid --create-hybrid-pipeline --title "Quantum groups" --abstract "This paper studies representations and cohomology."
```


## Dummy User Manuscript Search

For a realistic user manuscript, the dummy user search uses only:

```text
Title
Abstract
```

It does not use MSC codes, journal name, venue, or ISSN.

Command:

```powershell
python -m core.search.run_dummy_user_hybrid_search --top-k 50 --dense-k 100
```

Custom input:

```powershell
python -m core.search.run_dummy_user_hybrid_search --title "Your title" --abstract "Your abstract" --top-k 50
```

Output:

```text
output/user_queries/dummy_user_hybrid_results.json
```

Each result contains:

```text
hybrid_score
title
year
authors
journal_name
venue
issn
doi
abstract
```


## Evaluation

Evaluation uses leave-one-out retrieval:

1. Take a record from the indexed dataset.
2. Use it as the query.
3. Retrieve top-k results.
4. Remove the query record itself.
5. Mark results relevant according to the workflow's relevance rule.
6. Compute ranking metrics.


### MSC Relevance

Default:

```text
shared top-level MSC class
```

Example:

```text
17B56 and 17B37 are relevant because both are class 17.
```

Exact-code mode is also supported:

```powershell
python -m core.evaluation.evaluate_msc_hybrid_opensearch --relevance-mode exact
```


### no-MSC Relevance

Relevant if:

```text
same ISSN
```

Fallback:

```text
same normalized venue
```


## Evaluation Metrics

### precision@k

```text
relevant results in top k / k
```

Measures how many recommendations in the top-k are relevant.


### recall@k

```text
relevant results in top k / total relevant results in corpus
```

Can look low when there are many relevant records in the corpus. For MSC,
top-level classes can contain hundreds of relevant papers, so recall@10 or
recall@50 may be low even when ranking quality is good.


### MRR@k

Mean reciprocal rank of the first relevant result.

If the first relevant result is rank 1:

```text
MRR contribution = 1.0
```

If first relevant result is rank 5:

```text
MRR contribution = 0.2
```


### nDCG@k

Normalized discounted cumulative gain. It rewards relevant results appearing
near the top more than relevant results appearing lower down.


## Current MSC Evaluation Findings

For `@50` on 50 evaluated queries:

```text
keyword_only:
precision@50 = 0.2304
recall@50    = 0.0233
mrr@50       = 0.6117
ndcg@50      = 0.2693

vector_only:
precision@50 = 0.7516
recall@50    = 0.0930
mrr@50       = 0.9767
ndcg@50      = 0.7843

hybrid_50_50:
precision@50 = 0.7392
recall@50    = 0.0916
mrr@50       = 0.9767
ndcg@50      = 0.7758

hybrid_70_30:
precision@50 = 0.7392
recall@50    = 0.0916
mrr@50       = 0.9767
ndcg@50      = 0.7758
```

Vector-only is currently the strongest MSC retrieval mode.

Reason:

- MSC embeddings include MSC codes and descriptions.
- Evaluation rewards MSC similarity.
- Dense vectors capture this subject-area similarity better than BM25.
- Adding BM25 in hybrid mode adds some noise and slightly lowers precision/nDCG.


## Evaluation Reports

MSC report:

```text
output/opensearch_evaluation_msc/hybrid_evaluation_report.html
```

no-MSC report:

```text
output/opensearch_evaluation/hybrid_evaluation_report.html
```

Generate MSC report:

```powershell
python -m core.evaluation.evaluate_msc_hybrid_opensearch --k 50 --limit 50
python -m core.evaluation.visualize_msc_hybrid_evaluation
```


## OpenSearch Preview Tables

Export MSC index preview:

```powershell
python -m core.evaluation.export_msc_opensearch_table
```

Output:

```text
output/opensearch_preview/journal_recommender_msc.html
output/opensearch_preview/journal_recommender_msc.csv
```

Export more rows:

```powershell
python -m core.evaluation.export_msc_opensearch_table --size 500
```


## Recommended End-To-End MSC Workflow

Run this when rebuilding from scratch:

```powershell
python -m ingestion.metadata.run_msc_pipeline
python -m ingestion.embeddings.create_msc_embeddings
python -m ingestion.indexing.index_msc_opensearch --recreate
python -m core.evaluation.export_msc_opensearch_table
```

Then run a user manuscript search:

```powershell
python -m core.search.run_dummy_user_hybrid_search --top-k 50 --dense-k 100
```

Then evaluate:

```powershell
python -m core.evaluation.evaluate_msc_hybrid_opensearch --k 50 --limit 50
python -m core.evaluation.visualize_msc_hybrid_evaluation
```


## Important Notes

1. Always use `--recreate` when re-indexing after metadata or embedding changes.

2. `raw.jsonl` can contain records without ISSN. `clean.jsonl` is the
   journal-ready ISSN-filtered dataset.

3. `venue` is not always a clean journal name. Use `journal_name` and `issn`
   for journal identity.

4. Dense MSC embeddings intentionally exclude `journal_name` to avoid journal
   identity leakage into semantic vectors.

5. If Hugging Face network access is blocked but the model is cached locally,
   run with offline environment variables:

   ```powershell
   $env:HF_HUB_OFFLINE='1'
   $env:TRANSFORMERS_OFFLINE='1'
   ```

6. If metadata collection causes DNS/rate-limit problems, reduce pipeline
   concurrency from `32` to `16`.


## More Detailed Evaluation Documentation

See:

```text
docs/opensearch_hybrid_search_evaluation.md
output/opensearch_evaluation/evaluation_metrics_explained.txt
```
