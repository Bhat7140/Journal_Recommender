import argparse
import json
from pathlib import Path

from configs.embedding_config import BASE_DIR, EMBEDDING_MODEL_NAME
from configs.opensearch_config import (
    MSC_HYBRID_PIPELINE_NAME,
    MSC_INDEX_NAME,
    OPENSEARCH_HOST,
    OPENSEARCH_PASSWORD,
    OPENSEARCH_PORT,
    OPENSEARCH_USE_SSL,
    OPENSEARCH_USER,
    OPENSEARCH_VERIFY_CERTS,
)
from ingestion.embeddings.embedding_common import load_embedding_model
from core.search.opensearch_backend import (
    create_hybrid_search_pipeline,
    hybrid_search,
    load_opensearch_client,
)


DEFAULT_TITLE = "Cohomology and representations of quantum groups"
DEFAULT_ABSTRACT = (
    "This manuscript studies cohomological methods for quantum groups and "
    "related algebraic structures. We investigate representations, homological "
    "invariants, and connections with Lie algebra cohomology."
)
MANUSCRIPT_LEXICAL_FIELDS = ["title^3", "abstract"]
SOURCE_FIELDS = [
    "title",
    "year",
    "authors",
    "journal_name",
    "venue",
    "issn",
    "doi",
    "abstract",
]


def user_query_text(title, abstract):
    return "\n".join(
        part
        for part in [
            f"Title: {title or ''}",
            f"Abstract: {abstract or ''}",
        ]
        if part.split(": ", 1)[-1]
    ).strip()


def format_hit(hit):
    source = hit.get("_source", {})
    return {
        "hybrid_score": hit.get("_score"),
        "title": source.get("title"),
        "year": source.get("year"),
        "authors": source.get("authors") or [],
        "journal_name": source.get("journal_name"),
        "venue": source.get("venue"),
        "issn": source.get("issn") or [],
        "doi": source.get("doi"),
        "abstract": source.get("abstract"),
    }


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Run title+abstract-only dummy user hybrid search against the MSC OpenSearch index."
    )
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--abstract", default=DEFAULT_ABSTRACT)
    parser.add_argument("--index-name", default=MSC_INDEX_NAME)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--dense-k", type=int, default=50)
    parser.add_argument("--model", default=EMBEDDING_MODEL_NAME)
    parser.add_argument("--hybrid-pipeline", default=MSC_HYBRID_PIPELINE_NAME)
    parser.add_argument("--create-hybrid-pipeline", action="store_true")
    parser.add_argument("--bm25-weight", type=float, default=0.5)
    parser.add_argument("--dense-weight", type=float, default=0.5)
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE_DIR / "output" / "user_queries" / "dummy_user_hybrid_results.json",
    )
    parser.add_argument("--host", default=OPENSEARCH_HOST)
    parser.add_argument("--port", type=int, default=OPENSEARCH_PORT)
    parser.add_argument("--user", default=OPENSEARCH_USER)
    parser.add_argument("--password", default=OPENSEARCH_PASSWORD)
    parser.add_argument("--no-ssl", action="store_true")
    parser.add_argument("--verify-certs", action="store_true", default=OPENSEARCH_VERIFY_CERTS)

    args = parser.parse_args()
    query_text = user_query_text(args.title, args.abstract)

    client = load_opensearch_client(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        use_ssl=OPENSEARCH_USE_SSL and not args.no_ssl,
        verify_certs=args.verify_certs,
    )

    if args.create_hybrid_pipeline:
        create_hybrid_search_pipeline(
            client=client,
            pipeline_name=args.hybrid_pipeline,
            bm25_weight=args.bm25_weight,
            dense_weight=args.dense_weight,
        )

    model = load_embedding_model(args.model)
    query_embedding = model.encode(
        query_text,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    response = hybrid_search(
        client=client,
        index_name=args.index_name,
        query_text=query_text,
        query_embedding=query_embedding,
        top_k=args.top_k,
        search_pipeline=args.hybrid_pipeline,
        source_fields=SOURCE_FIELDS,
        lexical_fields=MANUSCRIPT_LEXICAL_FIELDS,
        dense_k=args.dense_k,
    )

    output = {
        "user_query": {
            "title": args.title,
            "abstract": args.abstract,
            "embedding_text": query_text,
        },
        "search": {
            "index_name": args.index_name,
            "hybrid_pipeline": args.hybrid_pipeline,
            "bm25_weight": args.bm25_weight,
            "dense_weight": args.dense_weight,
            "top_k": args.top_k,
            "dense_k": args.dense_k,
            "lexical_fields": MANUSCRIPT_LEXICAL_FIELDS,
        },
        "results": [
            format_hit(hit)
            for hit in response["hits"]["hits"]
        ],
    }
    write_json(args.output, output)

    print("[DONE] dummy user hybrid search")
    print(f"  results : {args.output}")
    print(f"  hits    : {len(output['results'])}")


if __name__ == "__main__":
    main()
