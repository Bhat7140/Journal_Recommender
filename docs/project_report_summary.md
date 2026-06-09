CAn # Math Journal Recommender: Project Report Summary

## 1. Project Motivation

The goal of this project is to build a domain-specific journal recommender for
mathematics. Given a manuscript-like input, especially a title and abstract, the
system should retrieve related mathematical publications and use them as
evidence for journal recommendation.

The project focuses on mathematics because mathematical publications have
structured subject information through Mathematics Subject Classification
codes. These MSC codes provide a useful domain signal for representing the
topic of a paper.

The final system is designed around this idea:

- retrieve papers that are mathematically similar to the input manuscript
- keep only records that can be mapped back to actual journals
- use ISSN as the stable journal identifier
- expose journal name, ISSN, DOI, and supporting publication evidence


## 2. Central Problem

A journal recommender needs more than general semantic similarity. It needs a
reliable way to map retrieved papers back to journals.

The raw metadata collected from scholarly APIs contains many records that are
not directly useful for journal recommendation:

- books
- proceedings
- chapters
- records without ISSN
- records with incomplete metadata
- citation-like venue strings instead of clean journal names

Because of this, the project treats ISSN as a required field for the final
recommender dataset. If a record has no ISSN, the system cannot reliably map it
back to a journal, so it is excluded from the clean dataset.


## 3. Main Concepts Used

### Metadata Retrieval

Metadata is collected from external scholarly sources:

- zbMATH
- Crossref
- OpenAlex
- arXiv, mainly for physics experiments

zbMATH is especially important for mathematics because it provides MSC subject
codes. Crossref and OpenAlex are used to enrich records with DOI, ISSN, source,
and journal information.


### Normalization

Different APIs return metadata in different formats. The project normalizes all
records into a common `Work` structure containing:

- title
- abstract
- year
- authors
- venue
- subjects / MSC codes
- DOI
- ISSN
- source flags
- journal name

This common model makes later embedding, indexing, and evaluation steps simpler.


### ISSN-Based Journal Identity

ISSN is used as the stable journal identifier.

This is important because venue strings are often inconsistent. A venue may be:

- a clean journal name
- a full citation
- a book series
- a proceedings title
- a string with volume, issue, pages, and year

The project therefore resolves journal names from ISSN when possible and stores
both:

- `issn`
- `journal_name`


### Transformer Embeddings

The project uses:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Each paper is converted into text and embedded as a dense vector. The dense
vector is used for semantic retrieval.

For the MSC workflow, the embedding text contains:

- title
- MSC codes
- MSC descriptions
- venue
- abstract

The dense embedding intentionally does not include `journal_name`. This avoids
leaking journal identity into the semantic representation. Journal name is kept
as metadata and can still be used for display, filtering, keyword search, and
aggregation.


### OpenSearch

OpenSearch is used as the retrieval backend. It stores:

- metadata fields
- journal identity fields
- dense vector embeddings

OpenSearch supports:

- BM25 keyword search
- k-nearest-neighbor vector search
- hybrid search using score normalization


### Hybrid Search

Hybrid search combines two retrieval branches:

1. BM25 keyword search
2. Dense vector similarity search

The project evaluates hybrid search with different weights:

- 50% BM25, 50% dense vector
- 70% BM25, 30% dense vector

The hybrid scores are produced by OpenSearch using a search pipeline that
normalizes and combines scores.


## 4. Implementation Process

### Step 1: Build Metadata Sources

The project first implemented wrappers for scholarly APIs:

- `ZBMathSource`
- `CrossrefSource`
- `OpenAlexSource`
- `ArxivSource`

Each source has methods to:

- search records
- fetch records by DOI when possible
- normalize raw API responses into the `Work` model


### Step 2: Build A Core Pipeline

A reusable pipeline was implemented to:

1. search the primary source
2. normalize records
3. enrich records using DOI lookups
4. merge duplicate/enriched records
5. output normalized metadata

The pipeline was later parallelized because metadata collection became slow
after increasing the retrieval limit from 100 to 1000 records per query.

Parallelization was added for:

- source pagination
- DOI enrichment
- ISSN journal-name lookup


### Step 3: Add ISSN And Journal Cleanup

The project then introduced a journal-focused cleanup stage.

This cleanup:

- normalizes ISSN values
- removes records without ISSN
- resolves journal names from ISSN
- keeps only records with useful abstracts

This reduced the dataset size, but improved journal reliability. For example,
the MSC clean dataset currently contains over ten thousand records and has no
missing ISSN values.


### Step 4: Create Embeddings

The cleaned metadata is converted into embedding text.

For MSC records, the embedding text is mathematically enriched using MSC codes
and top-level MSC descriptions.

Example structure:

```text
Title: ...
MSC codes: ...
MSC descriptions: ...
Venue: ...
Abstract: ...
```

The resulting vectors are saved as:

```text
embeddings.npy
works.jsonl
embedding_metadata.json
```


### Step 5: Index Into OpenSearch

The indexed OpenSearch documents contain:

- work ID
- embedding ID
- title
- abstract
- year
- authors
- journal name
- venue
- ISSN
- DOI
- MSC subjects
- dense embedding vector

The index uses a `knn_vector` field for dense retrieval.

The MSC index currently contains:

```text
10920 records
384-dimensional embeddings
```


### Step 6: Implement Search

The project supports:

- keyword-only search
- vector-only search
- hybrid search

The search scripts allow testing with title, abstract, MSC codes, and other
metadata fields.

A separate dummy user search workflow was added for a realistic manuscript
input. It uses only:

- title
- abstract

It embeds the title and abstract using the same transformer model and searches
the MSC OpenSearch index.


### Step 7: Implement Evaluation

Evaluation was implemented to compare retrieval strategies.

The main evaluation method is leave-one-out retrieval:

1. take an indexed record as a query
2. search the OpenSearch index
3. remove the query record itself
4. mark returned results as relevant or not relevant
5. compute ranking metrics

For MSC evaluation, relevance is based on shared MSC class. For no-MSC
evaluation, relevance is based on same ISSN or same venue.


## 5. Evaluation Metrics

### Precision@k

Precision@k measures the fraction of top-k results that are relevant.

This is important for recommendation because users usually inspect only the
first few recommendations.


### Recall@k

Recall@k measures how many of all relevant records in the corpus were retrieved
within the top-k.

In this project, recall can look low for MSC because top-level MSC classes are
broad. A single query may have hundreds of relevant records, but the evaluation
only looks at the top 10 or top 50.


### MRR@k

Mean reciprocal rank measures how early the first relevant result appears.

High MRR means the system usually places a relevant result near the top.


### nDCG@k

nDCG measures ranking quality by rewarding relevant results near the top more
than relevant results lower in the list.


## 6. Main Experimental Findings

### no-MSC Workflow

The no-MSC workflow uses title, venue, and abstract, but does not include MSC
codes.

It performed weakly for same-journal or same-venue retrieval:

```text
precision@10 = 0.1688
MRR@10       = 0.3368
nDCG@10      = 0.2389
```

This means only about 1.7 of the top 10 results were same-journal or same-venue
matches on average.

This is not strong enough as a final journal recommender, but it is a useful
baseline.


### MSC Workflow

The MSC workflow performed much better because it includes mathematics-specific
subject information.

For the current @50 evaluation over 50 queries:

```text
vector_only:
precision@50 = 0.7516
recall@50    = 0.0930
MRR@50       = 0.9767
nDCG@50      = 0.7843
```

Hybrid search was slightly weaker:

```text
hybrid_50_50:
precision@50 = 0.7392
recall@50    = 0.0916
MRR@50       = 0.9767
nDCG@50      = 0.7758
```

This suggests that dense vector retrieval is currently the strongest retrieval
mode for MSC-based mathematical similarity.


## 7. Why Vector Search Performs Best For MSC

Vector search performs best because the dense embeddings are MSC-aware.

The embeddings include:

- MSC codes
- MSC descriptions
- title
- abstract

The evaluation also rewards MSC similarity. Therefore, the dense vector
representation and the evaluation target are aligned.

BM25 keyword search is weaker because it depends more on exact token overlap.
Dense retrieval can capture broader mathematical similarity even when two
papers do not share identical words.

Hybrid search did not outperform vector-only because adding BM25 introduced
some keyword-based noise into an already strong dense retrieval result.


## 8. Why Recall Is Low

MSC recall is low even when the ranking is good because many records can share
the same top-level MSC class.

Example:

```text
If 500 papers share MSC class 17,
and the system returns 45 relevant papers in the top 50,
recall@50 = 45 / 500 = 0.09.
```

This is not necessarily bad. For a recommender, precision, MRR, and nDCG are
more informative because they measure the quality of the top-ranked results.


## 9. Important Design Decisions

### Keep Only ISSN Records

This was necessary because the system is a journal recommender. Without ISSN,
there is no reliable journal identity to recommend.


### Keep Raw And Clean Data Separate

Raw data preserves everything collected.

Clean data is journal-ready:

- has abstract
- has ISSN
- can support journal recommendation


### Do Not Embed Journal Name In MSC Vectors

Journal name was removed from MSC embedding text to avoid bias. If the dense
vector included journal names, the model could learn journal identity rather
than mathematical content.

Instead:

- dense vectors represent mathematical content
- journal name is kept as metadata
- journal recommendation can be produced by aggregating retrieved papers by
  ISSN/journal


### Use OpenSearch As The Retrieval Engine

OpenSearch provides:

- scalable indexing
- keyword retrieval
- vector retrieval
- hybrid retrieval
- reusable search APIs

This makes the project closer to a deployable retrieval system than a purely
local experiment.


## 10. Current Outputs

The project produces several types of outputs:

### Metadata

```text
output/metadata/msc/raw.jsonl
output/metadata/msc/clean.jsonl
```

### Embeddings

```text
output/embeddings/msc_clean/works.jsonl
output/embeddings/msc_clean/embeddings.npy
output/embeddings/msc_clean/embedding_metadata.json
```

### OpenSearch Previews

```text
output/opensearch_preview/journal_recommender_msc.html
output/opensearch_preview/journal_recommender_msc.csv
```

### Evaluation Reports

```text
output/opensearch_evaluation_msc/hybrid_evaluation_report.html
```

### Dummy User Search Results

```text
output/user_queries/dummy_user_hybrid_results.json
```


## 11. Limitations

The project still has several limitations:

- metadata collection depends on external APIs and can be slow
- API records can be incomplete or inconsistent
- journal names are only as good as the ISSN lookup sources
- evaluation relevance is still a proxy
- MSC evaluation measures subject similarity, not direct journal acceptance
- hybrid weights did not improve over vector-only in current experiments
- full large-scale @50 evaluation can be slow


## 12. Future Work

Useful next steps include:

- aggregate retrieved papers by ISSN to produce journal-level recommendations
- rank journals by number and quality of supporting retrieved papers
- add journal-level statistics such as top supporting papers per journal
- compare exact MSC relevance against top-level MSC relevance
- add hit-rate@k
- optimize full-corpus evaluation for larger k
- test rank-fusion methods such as reciprocal rank fusion
- add a small web interface for manuscript input and journal result display
- create a final report that separates paper retrieval quality from journal
  recommendation quality


## 13. Final Summary

This project implements a complete retrieval-based math journal recommender
pipeline. It collects and cleans publication metadata, enforces ISSN-based
journal identity, creates MSC-aware transformer embeddings, indexes records in
OpenSearch, and evaluates keyword, vector, and hybrid retrieval strategies.

The strongest current result is MSC vector retrieval. It works well because the
embedding representation uses mathematical subject information and the
evaluation rewards mathematical subject similarity.

The next major step is to move from ranked similar papers to ranked journals by
aggregating retrieved evidence using ISSN and journal name.

