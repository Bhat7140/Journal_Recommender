import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

from configs.embedding_config import BASE_DIR
from configs.opensearch_config import (
    NO_MSC_EMBEDDING_DIR,
    NO_MSC_HYBRID_PIPELINE_NAME,
    NO_MSC_INDEX_NAME,
    OPENSEARCH_HOST,
    OPENSEARCH_PASSWORD,
    OPENSEARCH_PORT,
    OPENSEARCH_USE_SSL,
    OPENSEARCH_USER,
    OPENSEARCH_VERIFY_CERTS,
)
from ingestion.embeddings.create_no_msc_embeddings import text_for_no_msc_embedding
from core.search.opensearch_backend import (
    create_hybrid_search_pipeline,
    hybrid_search,
    stable_work_id,
)


SOURCE_FIELDS = [
    "work_id",
    "doi",
    "title",
    "abstract",
    "year",
    "authors",
    "journal_name",
    "venue",
    "issn",
    "subjects",
    "source",
]


SCENARIOS = [
    {
        "name": "hybrid_50_50",
        "bm25_weight": 0.5,
        "dense_weight": 0.5,
    },
    {
        "name": "hybrid_70_30",
        "bm25_weight": 0.7,
        "dense_weight": 0.3,
    },
]


def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return records


def normalize_text(value):
    if not value:
        return None
    return " ".join(str(value).lower().split())


def normalize_issn_values(value):
    if not value:
        return set()
    if not isinstance(value, list):
        value = [value]
    return {
        str(item).replace("-", "").strip().lower()
        for item in value
        if str(item).strip()
    }


def relevance_key(record):
    issn = normalize_issn_values(record.get("issn"))
    if issn:
        return ("issn", frozenset(issn))

    venue = normalize_text(record.get("venue"))
    if venue:
        return ("venue", venue)

    return None


def is_relevant(query_record, candidate_record):
    query_key = relevance_key(query_record)
    candidate_key = relevance_key(candidate_record)

    if not query_key or not candidate_key:
        return False

    query_kind, query_value = query_key
    candidate_kind, candidate_value = candidate_key

    if query_kind != candidate_kind:
        return False

    if query_kind == "issn":
        return bool(query_value & candidate_value)

    return query_value == candidate_value


def count_relevant(records, query_index):
    query_record = records[query_index]
    query_work_id = stable_work_id(query_record)
    total = 0

    for record in records:
        if stable_work_id(record) == query_work_id:
            continue
        if is_relevant(query_record, record):
            total += 1

    return total


def truncate_words(text, max_words):
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def query_text(record, max_abstract_words=None):
    # Match the document embedding format, but this still works for a user
    # title/abstract-style query because missing fields are omitted.
    abstract = record.get("abstract")
    if abstract and max_abstract_words:
        abstract = truncate_words(str(abstract), max_abstract_words)

    return text_for_no_msc_embedding(
        {
            "title": record.get("title"),
            "journal_name": record.get("journal_name"),
            "venue": record.get("venue"),
            "abstract": abstract,
        }
    )


def dcg(relevance_flags):
    score = 0.0
    for index, relevant in enumerate(relevance_flags, start=1):
        if relevant:
            score += 1.0 / math.log2(index + 1)
    return score


def evaluate_query(records, query_index, hits, k):
    query_record = records[query_index]
    query_work_id = stable_work_id(query_record)
    total_relevant = count_relevant(records, query_index)

    filtered_hits = []
    for hit in hits:
        source = hit.get("_source", {})
        if source.get("work_id") == query_work_id:
            continue
        filtered_hits.append(hit)
        if len(filtered_hits) == k:
            break

    relevance_flags = [
        is_relevant(query_record, hit.get("_source", {}))
        for hit in filtered_hits
    ]

    relevant_found = sum(1 for value in relevance_flags if value)
    precision = relevant_found / k if k else 0.0
    recall = relevant_found / total_relevant if total_relevant else 0.0

    reciprocal_rank = 0.0
    for rank, relevant in enumerate(relevance_flags, start=1):
        if relevant:
            reciprocal_rank = 1.0 / rank
            break

    ideal_relevant_count = min(total_relevant, k)
    ideal_dcg = dcg([True] * ideal_relevant_count)
    ndcg = dcg(relevance_flags) / ideal_dcg if ideal_dcg else 0.0

    return {
        "query_work_id": query_work_id,
        "relevance_type": relevance_key(query_record)[0],
        "total_relevant": total_relevant,
        f"precision@{k}": precision,
        f"recall@{k}": recall,
        f"mrr@{k}": reciprocal_rank,
        f"ndcg@{k}": ndcg,
        f"relevant_found@{k}": relevant_found,
    }


def average_metric(rows, key):
    if not rows:
        return 0.0
    return sum(row[key] for row in rows) / len(rows)


def write_csv(path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate no-MSC OpenSearch hybrid search with venue/ISSN relevance."
    )
    parser.add_argument("--index-name", default=NO_MSC_INDEX_NAME)
    parser.add_argument("--embedding-dir", type=Path, default=NO_MSC_EMBEDDING_DIR)
    parser.add_argument("--pipeline-prefix", default=NO_MSC_HYBRID_PIPELINE_NAME)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--dense-k", type=int, default=50)
    parser.add_argument(
        "--max-abstract-words",
        type=int,
        default=200,
        help="Limit abstract words in evaluation queries to avoid huge BM25 clauses.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Evaluate only the first N usable queries. Defaults to all usable records.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BASE_DIR / "output" / "opensearch_evaluation",
    )
    parser.add_argument("--host", default=OPENSEARCH_HOST)
    parser.add_argument("--port", type=int, default=OPENSEARCH_PORT)
    parser.add_argument("--user", default=OPENSEARCH_USER)
    parser.add_argument("--password", default=OPENSEARCH_PASSWORD)
    parser.add_argument("--no-ssl", action="store_true")
    parser.add_argument("--verify-certs", action="store_true", default=OPENSEARCH_VERIFY_CERTS)

    args = parser.parse_args()

    from core.search.opensearch_backend import load_opensearch_client

    records = load_jsonl(args.embedding_dir / "works.jsonl")
    embeddings = np.load(args.embedding_dir / "embeddings.npy")

    if len(records) != len(embeddings):
        raise ValueError(
            f"Record/vector count mismatch: {len(records)} records, "
            f"{len(embeddings)} embeddings"
        )

    usable_indices = [
        index
        for index, record in enumerate(records)
        if (
            relevance_key(record)
            and query_text(record, args.max_abstract_words)
            and count_relevant(records, index) > 0
        )
    ]
    if args.limit:
        usable_indices = usable_indices[: args.limit]

    client = load_opensearch_client(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        use_ssl=OPENSEARCH_USE_SSL and not args.no_ssl,
        verify_certs=args.verify_certs,
    )

    summary_rows = []

    for scenario in SCENARIOS:
        pipeline_name = f"{args.pipeline_prefix}_{scenario['name']}"
        create_hybrid_search_pipeline(
            client=client,
            pipeline_name=pipeline_name,
            bm25_weight=scenario["bm25_weight"],
            dense_weight=scenario["dense_weight"],
        )

        detail_rows = []
        for query_count, query_index in enumerate(usable_indices, start=1):
            response = hybrid_search(
                client=client,
                index_name=args.index_name,
                query_text=query_text(records[query_index], args.max_abstract_words),
                query_embedding=embeddings[query_index],
                top_k=args.k + 1,
                search_pipeline=pipeline_name,
                source_fields=SOURCE_FIELDS,
                dense_k=args.dense_k,
            )

            row = evaluate_query(
                records=records,
                query_index=query_index,
                hits=response["hits"]["hits"],
                k=args.k,
            )
            row = {
                "scenario": scenario["name"],
                "query_number": query_count,
                **row,
            }
            detail_rows.append(row)

        metric_keys = [
            f"precision@{args.k}",
            f"recall@{args.k}",
            f"mrr@{args.k}",
            f"ndcg@{args.k}",
        ]
        summary_rows.append(
            {
                "scenario": scenario["name"],
                "bm25_weight": scenario["bm25_weight"],
                "dense_weight": scenario["dense_weight"],
                "queries": len(detail_rows),
                **{
                    key: average_metric(detail_rows, key)
                    for key in metric_keys
                },
            }
        )

        detail_path = args.output_dir / f"{scenario['name']}_details.csv"
        write_csv(detail_path, detail_rows)

    summary_path = args.output_dir / "summary.csv"
    write_csv(summary_path, summary_rows)

    print("[DONE] no-MSC hybrid evaluation")
    print(f"  queries evaluated : {len(usable_indices)}")
    print(f"  summary csv       : {summary_path}")
    for row in summary_rows:
        print(
            f"  {row['scenario']}: "
            f"precision@{args.k}={row[f'precision@{args.k}']:.4f} "
            f"recall@{args.k}={row[f'recall@{args.k}']:.4f} "
            f"mrr@{args.k}={row[f'mrr@{args.k}']:.4f} "
            f"ndcg@{args.k}={row[f'ndcg@{args.k}']:.4f}"
        )


if __name__ == "__main__":
    main()
