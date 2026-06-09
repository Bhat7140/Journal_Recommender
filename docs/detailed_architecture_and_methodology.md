# Detailed Architecture And Methodology

## 1. Purpose Of This Document

This document explains the design choices behind the journal recommender
pipeline in more detail than the README. It focuses on:

- how metadata is collected
- why the metadata pipeline has multiple layers
- why ISSN cleanup is required
- why the mathematics workflow was split into MSC and no-MSC variants
- why the project settled on MSC as the main math workflow
- how physics metadata is handled differently from math metadata
- why the embedding text structures were chosen
- what challenges appeared during implementation
- how OpenSearch is used for indexing, retrieval, hybrid search, and
  evaluation

The goal is to make the project explainable in a science report or
presentation, not only runnable as software.


## 2. Overall Problem Framing

The project is a domain-specific journal recommender. The input is a
manuscript-like record, typically:

```text
Title
Abstract
```

The output should be a ranked list of journal-related recommendations supported
by similar papers in the indexed corpus.

The recommender is not trying to solve general web search. It is trying to
answer a narrower question:

```text
Given this mathematical manuscript, which journals have published similar work?
```

This distinction affects the entire design. A general paper search engine can
return books, proceedings, preprints, or papers without clear journal identity.
A journal recommender needs every indexed item to map back to a journal.

That is why the project gives special importance to:

- ISSN
- journal name
- DOI
- abstract
- subject classification


## 3. Why Metadata Quality Matters More Than Raw Quantity

At first, it may seem best to collect as many records as possible. However, for
journal recommendation, more data is not always better.

Many scholarly metadata records are not useful as journal recommendation
evidence:

- books
- book chapters
- conference proceedings
- old records without ISSN
- records with missing abstracts
- records with citation strings instead of clean journal names
- records that cannot be mapped back to a serial journal

If these records are indexed, retrieval quality can look larger in volume but
weaker in recommendation value. The system may retrieve mathematically related
items, but if those items do not map to journals, they cannot support a final
journal recommendation.

Therefore the pipeline deliberately separates:

```text
raw metadata
clean journal-ready metadata
```

The raw metadata is preserved for auditing and debugging. The clean metadata is
used for embeddings and OpenSearch indexing.


## 4. Multi-Layer Metadata Collection

The metadata workflow is multi-layered because no single source provides all
fields reliably.

The project uses a primary source to find candidate records, then enrichment
sources to fill missing fields.

Conceptually:

```text
primary source search
    -> normalize record
    -> DOI-based enrichment
    -> merge fields from multiple sources
    -> ISSN and journal cleanup
    -> write JSONL output
```


### 4.1 Primary Search Layer

The primary source is responsible for finding records relevant to a query.

For mathematics, the primary source is usually zbMATH because zbMATH is
mathematics-specific and provides MSC codes.

For physics, the primary source is split between OpenAlex and arXiv because
physics has different metadata patterns and arXiv is a major source for physics
preprints.


### 4.2 Normalization Layer

Each metadata API has a different response shape. The pipeline normalizes all
sources into one common `Work` model:

```python
Work(
    doi,
    title,
    abstract,
    year,
    authors,
    venue,
    subjects,
    issn,
    source,
    journal_name,
)
```

This is important because the rest of the pipeline should not need to know
whether a record came from zbMATH, Crossref, OpenAlex, or arXiv.


### 4.3 Enrichment Layer

The enrichment layer uses DOI lookup to improve metadata quality.

Example:

```text
zbMATH record
    has: title, abstract/review, MSC codes, sometimes DOI
    missing: clean ISSN, clean journal name

Crossref/OpenAlex enrichment
    can add: ISSN, journal/source name, cleaner DOI metadata
```

This is why enrichment is layered rather than replacing the primary source.
zbMATH is good for math subject metadata, while Crossref/OpenAlex are better for
journal identifiers.


### 4.4 Merge Layer

When the same work appears in multiple sources, the pipeline merges records.

The merge logic prefers:

- existing DOI if available
- non-empty title, abstract, venue
- longer author list
- combined ISSN list
- combined source flags
- journal name from any source that provides it

The aim is not to treat API records as competing versions, but as partial views
of the same publication.


### 4.5 Cleanup Layer

After collection and enrichment, records are cleaned for final use.

The clean metadata requires:

- useful abstract
- non-empty ISSN

ISSNs are normalized into a consistent form:

```text
0002-9939
```

Journal names are resolved from ISSN using Crossref and OpenAlex where
possible.


## 5. Why ISSN Is Central

ISSN is the key journal identity field.

The project uses ISSN because:

- it identifies a serial publication
- it is more stable than venue strings
- one journal may have print and electronic ISSNs
- it allows grouping retrieved papers by journal
- it makes recommendation output actionable

Without ISSN, a record may still be useful for topic retrieval, but not for
journal recommendation.

For example, a record may have:

```text
Venue: Proc. Am. Math. Soc. 138, No. 1, 85-99 (2010)
```

This is useful text, but it is not a clean identifier. The ISSN makes it
possible to say:

```text
This result belongs to this journal.
```

This is why the clean dataset excludes records with missing ISSN.


## 6. Mathematics Workflow

The mathematics workflow has two variants:

- no-MSC
- MSC

This split was useful experimentally because it allowed comparison between
general metadata-only retrieval and retrieval using mathematical classification
signals.


## 7. no-MSC Math Workflow

The no-MSC workflow uses mathematical keyword queries but does not include MSC
codes in the embedding text.

The embedding text contains:

```text
Title
Venue
Abstract
```

This workflow is useful as a baseline because it answers:

```text
How well can we retrieve related math records without explicit classification?
```

However, the no-MSC workflow performed weaker in evaluation. It does not have a
structured mathematical topic signal, so semantic similarity depends mostly on
title and abstract language.

It is also evaluated using same-ISSN or same-venue relevance, which is a strict
journal-level proxy.


## 8. MSC Math Workflow

The MSC workflow is the main workflow for mathematics.

It uses MSC codes collected from zbMATH and enriches them with top-level MSC
descriptions.

The embedding text contains:

```text
Title
MSC codes
MSC descriptions
Venue
Abstract
```

Example:

```text
Title: Cohomology of quantum groups
MSC codes: 17B37 17B56 20G05
MSC descriptions: 17: Nonassociative rings and algebras; 20: Group theory and generalizations
Venue: ...
Abstract: ...
```


## 9. Why MSC Was Chosen As The Main Math Structure

MSC was selected because mathematics has a mature and widely used
classification system.

MSC provides several advantages:

1. It gives explicit domain labels.
2. It reduces dependence on exact wording in abstracts.
3. It helps connect papers that are mathematically related but use different
   terminology.
4. It provides a natural relevance proxy for evaluation.
5. It makes the recommender more domain-specific rather than generic.

The experiments showed that MSC-aware retrieval is much stronger than the
no-MSC baseline. Vector retrieval in the MSC workflow achieved high precision
and nDCG because the embedding representation contained mathematical subject
information.


## 10. Why MSC Descriptions Are Included

MSC codes alone are symbolic:

```text
17B37
20G05
```

A general transformer model may not understand the meaning of these codes. To
make them semantically useful, the project adds top-level MSC descriptions.

This turns symbolic labels into natural-language context:

```text
17: Nonassociative rings and algebras
20: Group theory and generalizations
```

This helps the sentence transformer place papers from related mathematical
areas closer in vector space.


## 11. Why Journal Name Was Not Included In MSC Dense Embeddings

At one point, journal name was added to embedding text. This was later removed
from MSC embeddings.

Reason:

```text
journal_name in dense text can leak journal identity into the semantic vector
```

For a journal recommender, this can create bias. The system may retrieve papers
because they mention the same journal, not because they are mathematically
similar.

The final design is:

```text
dense embedding: mathematical content
metadata fields: journal identity
```

So `journal_name` remains in OpenSearch metadata and BM25 fields, but not in
the MSC dense embedding input.


## 12. Physics Workflow

Physics is handled differently from mathematics because physics does not use
MSC codes.

The physics workflow uses:

- OpenAlex topic/field filters
- Crossref metadata filters
- arXiv category queries

Physics collection is therefore based on source-specific domain filtering
rather than a classification system equivalent to MSC.


## 13. Why Physics Sources Were Selected

### OpenAlex

OpenAlex was selected for physics because it supports broad scholarly search
and topic/field metadata. It can filter records toward physics and astronomy.

### arXiv

arXiv was selected because physics heavily uses arXiv preprints. Many physics
papers appear on arXiv before or alongside journal publication.

### Crossref

Crossref was selected as an enrichment source because it is strong for DOI,
ISSN, and journal container metadata.


## 14. Difference Between Math And Physics Handling

Mathematics:

```text
primary source: zbMATH
domain signal: MSC codes
embedding structure: title + MSC codes + MSC descriptions + venue + abstract
main goal: math journal recommendation
```

Physics:

```text
primary sources: OpenAlex and arXiv
domain signal: OpenAlex fields, arXiv categories, subject labels
embedding structure: title + subjects + journal/venue + abstract
main goal: experimental comparison / broader scientific metadata workflow
```

The mathematics workflow is more structured because MSC gives a clean domain
taxonomy. Physics relies more on source-specific categorization.


## 15. Metadata Collection Challenges

Several practical challenges appeared during development.


### 15.1 API Inconsistency

Different APIs return different field names and nested structures.

For example:

- Crossref uses `container-title`
- OpenAlex uses `primary_location.source.display_name`
- zbMATH uses nested source and contributor structures

This required source-specific normalizers.


### 15.2 Missing Fields

Many records have missing:

- DOI
- ISSN
- abstract
- journal name
- source information

The pipeline had to be defensive. OpenAlex in particular can return `None` for
nested fields such as `primary_location` or `source`.


### 15.3 Venue Strings Are Noisy

Venue strings are not reliable journal identifiers. They may contain:

- volume
- issue
- pages
- year
- publisher
- book title
- conference title

This motivated the ISSN-based cleanup.


### 15.4 Metadata Volume

Increasing the search limit from 100 to 1000 records per query made collection
more complete but also slower.

To address this, the pipeline was parallelized:

- parallel source pagination
- parallel DOI enrichment
- parallel ISSN lookup
- thread-local HTTP sessions


### 15.5 Network And Rate Limits

External API calls can fail due to:

- DNS failures
- rate limiting
- temporary API downtime
- blocked network access

The project uses retries, but long metadata collection still depends on API
availability.


### 15.6 Dataset Shrinkage After ISSN Filtering

The clean dataset can be much smaller than the raw dataset. This is expected
because the final recommender requires journal identity.

For journal recommendation, it is better to have fewer records that reliably
map to journals than many records that cannot support final recommendations.


## 16. Embedding Design

The embedding design follows the principle:

```text
encode content and domain meaning, not final recommendation identity
```

For MSC, this means:

- include title
- include abstract
- include MSC codes
- include MSC descriptions
- avoid journal name in dense text

The embedding should represent the mathematical content of a paper. Journal
identity is handled later through metadata and aggregation.


## 17. Why Use Sentence Transformers

The project uses `sentence-transformers/all-MiniLM-L6-v2` because it is:

- lightweight
- fast compared to larger models
- produces 384-dimensional embeddings
- suitable for semantic similarity
- easy to use locally

This model is a pragmatic choice for experimentation. Larger or domain-specific
models could be tested later.


## 18. Embedding Artifacts

Each embedding run produces:

```text
works.jsonl
embeddings.npy
embedding_metadata.json
```

`works.jsonl` stores the records that were actually embedded.

`embeddings.npy` stores the vector matrix.

`embedding_metadata.json` records:

- model name
- embedding shape
- run name
- normalized flag
- text fields used
- input metadata path

This makes embedding runs reproducible and auditable.


## 19. OpenSearch Design

OpenSearch is used because it supports both traditional text retrieval and
vector search in one system.

Each indexed document contains:

- metadata
- ISSN/journal fields
- source flags
- dense embedding vector

The key OpenSearch field is:

```text
embedding: knn_vector
```

This allows dense nearest-neighbor retrieval.


## 20. OpenSearch Mapping

The OpenSearch mapping stores fields according to how they are used.

Exact-match fields:

```text
work_id
embedding_id
doi
issn
subjects
```

Full-text fields:

```text
title
abstract
venue
journal_name
```

Vector field:

```text
embedding
```

This combination allows:

- exact filtering by ISSN or DOI
- text search over title and abstract
- journal name search
- vector similarity search


## 21. Search Modes In OpenSearch

### Keyword Search

Keyword search uses BM25.

For MSC records, BM25 searches:

```text
title^3
subjects^3
abstract
journal_name^2
venue^2
authors
```

The boosts mean that title and MSC subjects are treated as especially
important.


### Vector Search

Vector search embeds the query and compares it to stored document embeddings.

This is the strongest retrieval mode in current MSC experiments because the
document vectors contain MSC-aware mathematical information.


### Hybrid Search

Hybrid search combines keyword and dense retrieval.

The OpenSearch hybrid query contains:

1. a BM25 `multi_match` branch
2. a `knn` vector branch

The scores are combined using an OpenSearch search pipeline.


## 22. Hybrid Score Normalization

BM25 scores and vector scores are not naturally on the same scale.

Therefore the project creates an OpenSearch search pipeline using:

```text
normalization-processor
```

The current fusion method is:

```text
min_max normalization
arithmetic mean combination
```

Evaluated weights:

```text
0.5 BM25 / 0.5 dense
0.7 BM25 / 0.3 dense
```

In current MSC experiments, both hybrid settings produced identical aggregate
metrics, suggesting that changing the weights did not meaningfully change the
top-ranked relevance outcomes.


## 23. Why Vector Beat Hybrid In MSC Experiments

The MSC vector representation is already very strong because it includes:

- title
- abstract
- MSC codes
- MSC descriptions

The evaluation also rewards shared MSC class. Therefore, dense retrieval and
evaluation are strongly aligned.

BM25 adds exact keyword matching, but that can introduce noise. A paper may
match words in the query but be less aligned in MSC subject area.

This is why vector-only slightly outperformed hybrid in the current MSC
evaluation.


## 24. Dummy User Search Design

The dummy user search is intentionally realistic.

It only accepts:

```text
title
abstract
```

It does not include:

- MSC codes
- journal name
- venue
- ISSN

This reflects a user submitting a manuscript draft. The system embeds the title
and abstract using the same transformer model, searches OpenSearch, and writes
results to JSON.

The output contains:

- hybrid score
- title
- year
- authors
- journal name
- venue
- ISSN
- DOI
- abstract


## 25. Evaluation Design

The evaluation uses leave-one-out retrieval.

For each indexed record:

1. treat that record as a query
2. retrieve top-k results
3. remove the query record itself
4. mark results relevant based on a relevance rule
5. compute ranking metrics

For MSC:

```text
relevant = shares top-level MSC class
```

For no-MSC:

```text
relevant = same ISSN or same venue fallback
```


## 26. Evaluation Metrics

The project uses:

- precision@k
- recall@k
- MRR@k
- nDCG@k

Precision, MRR, and nDCG are especially important for recommendation because
they measure top-ranked quality.

Recall can look low in MSC evaluation because top-level MSC relevance creates
large relevant sets.


## 27. Current Results Summary

In the current MSC @50 evaluation over 50 queries:

```text
vector_only:
precision@50 = 0.7516
recall@50    = 0.0930
MRR@50       = 0.9767
nDCG@50      = 0.7843

hybrid_50_50:
precision@50 = 0.7392
recall@50    = 0.0916
MRR@50       = 0.9767
nDCG@50      = 0.7758

keyword_only:
precision@50 = 0.2304
recall@50    = 0.0233
MRR@50       = 0.6117
nDCG@50      = 0.2693
```

This shows:

- keyword-only is weakest
- vector-only is strongest
- hybrid is close to vector but slightly worse
- MSC-aware embeddings are effective


## 28. Why This Architecture Was Selected

The architecture was selected because it separates the problem into clear
stages:

```text
metadata quality
domain representation
retrieval backend
evaluation
recommendation output
```

This separation makes the system easier to reason about.

Metadata collection ensures journal identity.

Embedding design captures mathematical content.

OpenSearch provides scalable retrieval.

Evaluation tests whether retrieved papers are subject-relevant.

Future journal recommendation can aggregate retrieved papers by ISSN.


## 29. Remaining Challenges

The main remaining challenges are:

- turning paper-level retrieval into journal-level ranking
- handling journals with very different numbers of indexed papers
- avoiding popularity bias toward large journals
- improving full-corpus evaluation speed
- testing other fusion methods
- evaluating exact MSC relevance
- building a user-facing interface
- validating recommendations against real journal suitability


## 30. Final Methodological Summary

The project evolved from a metadata retrieval experiment into a structured
math-specific journal recommendation pipeline.

The key methodological decisions were:

1. Use zbMATH for math-specific metadata.
2. Use MSC codes as the central domain signal.
3. Enrich records with Crossref/OpenAlex for ISSN and journal identity.
4. Require ISSN for clean journal-ready data.
5. Use transformer embeddings to represent mathematical content.
6. Exclude journal name from MSC dense embeddings to reduce bias.
7. Store metadata and vectors in OpenSearch.
8. Compare keyword, vector, and hybrid retrieval.
9. Use evaluation metrics that reflect top-k recommendation quality.

The current evidence suggests that MSC-aware vector retrieval is the strongest
foundation for the recommender. The next step is to aggregate similar retrieved
papers into ranked journal recommendations using ISSN and journal name.

