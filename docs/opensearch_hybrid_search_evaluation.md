# OpenSearch Hybrid Search And Evaluation Documentation

This document summarizes the OpenSearch implementation, hybrid search setup,
evaluation metrics, experimental scenarios, results, and conclusions for the
journal recommender project.


## 1. Goal

The goal is to move from an experimental retrieval pipeline to an OpenSearch
pipeline that supports:

- BM25 keyword retrieval over metadata/text fields.
- Dense vector retrieval over transformer embeddings.
- Hybrid retrieval that combines BM25 and dense vector scores.
- Evaluation of different retrieval strategies.

Two workflows were evaluated:

- `no_msc`: embeddings created from title, venue, and abstract.
- `msc`: embeddings created from title, MSC codes, MSC descriptions, venue, and
  abstract.


## 2. OpenSearch Files And Responsibilities

### `configs/opensearch_config.py`

Stores OpenSearch connection settings and index names.

Important settings:

```python
OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200
OPENSEARCH_USER = "admin"
OPENSEARCH_PASSWORD = "admin"
OPENSEARCH_USE_SSL = False
OPENSEARCH_VERIFY_CERTS = False
```

no-MSC settings:

```python
NO_MSC_INDEX_NAME = "journal_recommender_no_msc"
NO_MSC_EMBEDDING_DIR = BASE_DIR / "output" / "embeddings" / "no_msc_clean"
NO_MSC_HYBRID_PIPELINE_NAME = "journal_recommender_no_msc_hybrid"
```

MSC settings:

```python
MSC_INDEX_NAME = "journal_recommender_msc"
MSC_EMBEDDING_DIR = BASE_DIR / "output" / "embeddings" / "msc_clean"
MSC_HYBRID_PIPELINE_NAME = "journal_recommender_msc_hybrid"
```


### `search_backends/opensearch_backend.py`

Reusable OpenSearch backend.

Main responsibilities:

- Connect to OpenSearch.
- Create vector-enabled indices.
- Bulk index metadata and embeddings.
- Run BM25 keyword search.
- Run dense vector search.
- Run hybrid BM25 + dense search.
- Create hybrid search pipelines.

Important functions:

```python
load_opensearch_client(...)
create_hybrid_search_pipeline(...)
create_no_msc_index(...)
bulk_index_embeddings(...)
keyword_search(...)
vector_search(...)
hybrid_search(...)
```

The index stores both metadata and embeddings:

```text
title
abstract
year
authors
venue
subjects
issn
source
embedding
```

The `embedding` field is an OpenSearch `knn_vector` field.


## 3. no-MSC Workflow

### Embedding Text

The no-MSC embedding text is created by:

```python
runners/create_no_msc_embeddings.py
```

Format:

```text
Title: ...
Venue: ...
Abstract: ...
```

Model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Stored output:

```text
output/embeddings/no_msc_clean/works.jsonl
output/embeddings/no_msc_clean/embeddings.npy
output/embeddings/no_msc_clean/embedding_metadata.json
```


### Indexing

Runner:

```text
runners/index_no_msc_opensearch.py
```

Command:

```powershell
python -m runners.index_no_msc_opensearch --recreate
```


### Searching

Runner:

```text
runners/search_no_msc_opensearch.py
```

Example hybrid search:

```powershell
python -m runners.search_no_msc_opensearch --mode hybrid --create-hybrid-pipeline --top-k 10 --title "Quantum groups and operator algebras" --abstract "This paper studies representations, cohomology, and algebraic structures related to noncommutative operator theory."
```

Modes:

```text
keyword
vector
hybrid
```


## 4. MSC Workflow

### Embedding Text

The MSC embedding text is created by:

```python
runners/create_msc_embeddings.py
```

Format:

```text
Title: ...
MSC codes: ...
MSC descriptions: ...
Venue: ...
Abstract: ...
```

This is important because the dense vector representation is explicitly
MSC-aware.

Model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Stored output:

```text
output/embeddings/msc_clean/works.jsonl
output/embeddings/msc_clean/embeddings.npy
output/embeddings/msc_clean/embedding_metadata.json
```


### Indexing

Runner:

```text
runners/index_msc_opensearch.py
```

Command:

```powershell
python -m runners.index_msc_opensearch --recreate
```

Indexed result from the run:

```text
index name : journal_recommender_msc
run name   : msc_clean
records    : 2106
indexed    : 2106
dimension  : 384
errors     : 0
```


### Searching

Runner:

```text
runners/search_msc_opensearch.py
```

Example:

```powershell
python -m runners.search_msc_opensearch --mode hybrid --create-hybrid-pipeline --title "Lie algebra cohomology" --subjects "17B56 20G05" --abstract "We study algebraic representations and quantum group cohomology."
```

Modes:

```text
keyword
vector
hybrid
```


## 5. Hybrid Search

OpenSearch supports hybrid search by combining multiple query branches.

In this project, hybrid search combines:

1. BM25 branch:

```json
{
  "multi_match": {
    "query": "...",
    "fields": ["title^3", "abstract", "venue^2", "authors"]
  }
}
```

For MSC, the fields include `subjects`:

```python
MSC_HYBRID_FIELDS = ["title^3", "subjects^3", "abstract", "venue^2", "authors"]
```

2. Dense vector branch:

```json
{
  "knn": {
    "embedding": {
      "vector": [...],
      "k": 50
    }
  }
}
```


### Hybrid Score Fusion

OpenSearch uses a search pipeline with the `normalization-processor`.

The pipeline:

- Normalizes BM25 and dense scores using `min_max`.
- Combines them using `arithmetic_mean`.
- Applies weights such as `0.5 / 0.5` or `0.7 / 0.3`.

Hybrid scenarios evaluated:

```text
hybrid_50_50 = 0.5 BM25 / 0.5 dense
hybrid_70_30 = 0.7 BM25 / 0.3 dense
```


## 6. Evaluation Method

The evaluation uses leave-one-out retrieval.

For each query record:

1. Use the record as the query.
2. Retrieve top-k results from OpenSearch.
3. Remove the query record itself from results.
4. Score the remaining top-k results against a relevance rule.


### no-MSC Relevance

Relevance rule:

```text
same ISSN
```

If ISSN is missing:

```text
same normalized venue
```

This evaluates whether retrieval finds papers from the same journal/venue.


### MSC Relevance

Default relevance rule:

```text
shared top-level MSC class
```

Example:

```text
17B56 and 17B37 are relevant because both are top-level class 17.
```

The MSC evaluator also supports stricter exact-code relevance:

```powershell
python -m runners.evaluate_msc_hybrid_opensearch --relevance-mode exact
```


## 7. Evaluation Metrics

### precision@10

Formula:

```text
relevant results in top 10 / 10
```

Meaning:

- Measures how many of the first 10 results are relevant.
- Important because users usually inspect only the top recommendations.

Example:

```text
precision@10 = 0.80
```

means 8 out of the top 10 results are relevant.


### recall@10

Formula:

```text
relevant results in top 10 / total relevant results in corpus
```

Meaning:

- Measures how much of the full relevant set appears in the top 10.
- Can be low when the corpus has many relevant records.

Important:

If a query has 200 relevant records in the corpus, the maximum possible
recall@10 is:

```text
10 / 200 = 0.05
```

So low recall@10 does not always mean bad top-k retrieval.


### MRR@10

Full name:

```text
mean reciprocal rank at 10
```

Formula:

```text
1 / rank of first relevant result
```

Meaning:

- Measures how soon the first relevant result appears.
- If the first relevant result is rank 1, score is 1.0.
- If the first relevant result is rank 5, score is 0.2.
- If no relevant result appears in top 10, score is 0.0.


### nDCG@10

Full name:

```text
normalized discounted cumulative gain at 10
```

Meaning:

- Measures ranking quality across the top 10.
- Relevant results near the top count more than relevant results near rank 10.
- Score is normalized between 0 and 1.


## 8. no-MSC Results

Evaluation:

```text
queries evaluated: 613
relevance: same ISSN, falling back to same venue
```

Results:

```text
hybrid_50_50:
precision@10 = 0.1688
recall@10    = 0.1641
mrr@10       = 0.3368
ndcg@10      = 0.2389

hybrid_70_30:
precision@10 = 0.1688
recall@10    = 0.1641
mrr@10       = 0.3368
ndcg@10      = 0.2389
```


### no-MSC Interpretation

`precision@10 = 0.1688` means about:

```text
1.7 out of 10 results
```

are same-journal/same-venue matches.

This is weak-to-moderate. It is useful as a baseline, but not strong enough as
a final journal recommender.

However, this evaluation is strict. A semantically relevant paper from a
different journal is counted as non-relevant.


## 9. MSC Results: Hybrid Only

Initial MSC hybrid evaluation:

```text
queries evaluated: 2097
relevance: shared top-level MSC class
```

Results:

```text
hybrid_50_50:
precision@10 = 0.8579
recall@10    = 0.0502
mrr@10       = 0.9679
ndcg@10      = 0.8792

hybrid_70_30:
precision@10 = 0.8579
recall@10    = 0.0502
mrr@10       = 0.9679
ndcg@10      = 0.8792
```

The two hybrid settings tied exactly in aggregate metrics.


### Why Did 50/50 And 70/30 Tie?

Different weights do not guarantee different rankings.

The likely reasons:

1. BM25 and dense retrieval returned very similar top candidates.
2. MSC text contains explicit MSC codes/descriptions, so both branches can find
   same-topic documents.
3. Top-level MSC relevance is broad, so small ranking changes may not affect
   binary metrics.
4. OpenSearch min-max normalization may compress score differences.
5. The metrics are binary-relevance metrics and may not capture fine-grained
   ordering differences.

The rankings may still differ internally. To verify true ranking equality, the
evaluator would need to save top-k retrieved document IDs for each scenario.


## 10. MSC Results: Keyword, Vector, Hybrid

The MSC evaluator was expanded to compare:

```text
keyword_only = full BM25
vector_only  = full dense vector
hybrid_50_50
hybrid_70_30
```

Full results:

```text
queries evaluated: 2097
relevance: shared top-level MSC class

keyword_only:
precision@10 = 0.4653
recall@10    = 0.0249
mrr@10       = 0.7387
ndcg@10      = 0.5017

vector_only:
precision@10 = 0.8767
recall@10    = 0.0516
mrr@10       = 0.9683
ndcg@10      = 0.8913

hybrid_50_50:
precision@10 = 0.8579
recall@10    = 0.0502
mrr@10       = 0.9679
ndcg@10      = 0.8792

hybrid_70_30:
precision@10 = 0.8579
recall@10    = 0.0502
mrr@10       = 0.9679
ndcg@10      = 0.8792
```


### Best MSC Scenario

The best MSC scenario is:

```text
vector_only
```

It beats hybrid on all main metrics:

```text
precision@10: 0.8767 vs 0.8579
recall@10:    0.0516 vs 0.0502
mrr@10:       0.9683 vs 0.9679
ndcg@10:      0.8913 vs 0.8792
```


### Why Is Vector-Only Best For MSC?

Vector-only is best mainly because the MSC embeddings are MSC-aware.

The dense embedding text includes:

```text
MSC codes
MSC descriptions
```

The evaluation also rewards MSC similarity:

```text
relevant = shared top-level MSC class
```

So the dense vector representation and the evaluation target are strongly
aligned.

BM25-only is weaker because it depends more on exact token overlap. Dense
retrieval can capture broader semantic similarity across titles, abstracts,
MSC codes, and MSC descriptions.

Hybrid is slightly worse than vector-only because BM25 adds some noise. If
vector search already retrieves very strong MSC-relevant results, adding BM25
can pull in keyword-matching documents that are slightly less relevant by MSC.


## 11. Why MSC Recall Is Low

MSC recall@10 is low:

```text
recall@10 = 0.0502 for hybrid
recall@10 = 0.0516 for vector-only
```

This is expected.

The relevance rule is broad:

```text
shared top-level MSC class
```

For common MSC classes, there may be hundreds of relevant records in the
corpus. Since recall@10 only looks at 10 results, the maximum possible recall
may be low.

Example:

```text
total relevant records = 200
relevant records found in top 10 = 10
recall@10 = 10 / 200 = 0.05
```

Therefore, MSC recall@10 is not the main quality indicator. The better
indicators here are:

```text
precision@10
MRR@10
nDCG@10
```

Those metrics are strong for MSC.


## 12. no-MSC Vs MSC Comparison

no-MSC:

```text
precision@10 = 0.1688
recall@10    = 0.1641
mrr@10       = 0.3368
ndcg@10      = 0.2389
```

MSC vector-only:

```text
precision@10 = 0.8767
recall@10    = 0.0516
mrr@10       = 0.9683
ndcg@10      = 0.8913
```

MSC hybrid:

```text
precision@10 = 0.8579
recall@10    = 0.0502
mrr@10       = 0.9679
ndcg@10      = 0.8792
```


### Interpretation

MSC is much better for subject-area recommendation.

Precision comparison:

```text
no-MSC hybrid: 0.1688
MSC hybrid:    0.8579
MSC vector:    0.8767
```

MRR comparison:

```text
no-MSC hybrid: 0.3368
MSC hybrid:    0.9679
MSC vector:    0.9683
```

nDCG comparison:

```text
no-MSC hybrid: 0.2389
MSC hybrid:    0.8792
MSC vector:    0.8913
```

The only metric where no-MSC looks higher is recall@10, but this is due to the
different relevance definitions. no-MSC has fewer same-venue relevant records,
while MSC top-level relevance can include many records. This makes MSC
recall@10 naturally lower.


## 13. Visualizations

no-MSC report:

```text
output/opensearch_evaluation/hybrid_evaluation_report.html
```

MSC report:

```text
output/opensearch_evaluation_msc/hybrid_evaluation_report.html
```

Visualization runner files:

```text
runners/visualize_no_msc_hybrid_evaluation.py
runners/visualize_msc_hybrid_evaluation.py
```

The reports include:

- Summary metric table.
- Bar chart for precision, recall, MRR, and nDCG.
- Relevant hits distribution.
- Per-query precision distribution.
- Per-query MRR distribution.
- Per-query nDCG distribution.


## 14. Useful Commands

Index no-MSC:

```powershell
python -m runners.index_no_msc_opensearch --recreate
```

Search no-MSC:

```powershell
python -m runners.search_no_msc_opensearch --mode hybrid --create-hybrid-pipeline --title "Quantum groups" --abstract "This paper studies representations and cohomology."
```

Evaluate no-MSC:

```powershell
python -m runners.evaluate_no_msc_hybrid_opensearch
```

Visualize no-MSC:

```powershell
python -m runners.visualize_no_msc_hybrid_evaluation
```

Index MSC:

```powershell
python -m runners.index_msc_opensearch --recreate
```

Search MSC:

```powershell
python -m runners.search_msc_opensearch --mode hybrid --create-hybrid-pipeline --title "Lie algebra cohomology" --subjects "17B56 20G05" --abstract "We study representations and quantum group cohomology."
```

Evaluate MSC:

```powershell
python -m runners.evaluate_msc_hybrid_opensearch
```

Evaluate MSC with exact MSC-code relevance:

```powershell
python -m runners.evaluate_msc_hybrid_opensearch --relevance-mode exact
```

Visualize MSC:

```powershell
python -m runners.visualize_msc_hybrid_evaluation
```


## 15. Conclusions

1. OpenSearch supports the intended retrieval setup:

   - BM25 keyword search.
   - Dense vector search.
   - Hybrid BM25 + dense search through a search pipeline.

2. no-MSC hybrid retrieval is currently weak-to-moderate for same-venue
   retrieval.

3. MSC retrieval is strong for subject-area recommendation.

4. MSC vector-only is the best-performing scenario so far.

5. Hybrid does not beat vector-only for MSC because the dense embeddings already
   contain MSC codes and descriptions, and the evaluation rewards MSC similarity.

6. MSC recall@10 is low but justified because top-level MSC relevance creates
   large relevant sets.

7. For MSC, the most meaningful quality metrics are:

   - precision@10
   - MRR@10
   - nDCG@10

8. For future evaluation, useful additions would be:

   - hit-rate@10
   - recall@50
   - recall@100
   - exact-MSC relevance comparison
   - storing retrieved document IDs to compare actual ranking differences
   - testing hybrid with other fusion methods such as RRF
