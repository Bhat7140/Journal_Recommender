import argparse

from configs.embedding_config import EMBEDDING_MODEL_NAME
from configs.opensearch_config import (
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
from ingestion.embeddings.embedding_common import load_embedding_model
from core.search.opensearch_backend import (
    create_hybrid_search_pipeline,
    hybrid_search,
    keyword_search,
    load_opensearch_client,
    vector_search,
)


SOURCE_FIELDS = [
    "work_id",
    "embedding_id",
    "embedding_run",
    "embedding_index",
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


def print_hits(response):
    for rank, hit in enumerate(response["hits"]["hits"], start=1):
        source = hit["_source"]
        title = source.get("title") or "(untitled)"
        year = source.get("year") or "n.d."
        doi = source.get("doi") or "no DOI"
        issn = source.get("issn") or []
        if isinstance(issn, list):
            issn = ", ".join(issn) if issn else "no ISSN"
        print(f"{rank}. score={hit['_score']:.4f} year={year} doi={doi} issn={issn}")
        print(f"   {title}")
        print(
            f"   work_id={source.get('work_id')} "
            f"embedding_id={source.get('embedding_id')} "
            f"embedding_index={source.get('embedding_index')}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Search the no-MSC OpenSearch index."
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Free-form query text. Optional when --title/--abstract are provided.",
    )
    parser.add_argument("--title", default=None)
    parser.add_argument("--venue", default=None)
    parser.add_argument("--abstract", default=None)
    parser.add_argument("--index-name", default=NO_MSC_INDEX_NAME)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument(
        "--mode",
        choices=["vector", "keyword", "hybrid"],
        default="vector",
        help="Use vector search, BM25 keyword search, or hybrid BM25+dense search.",
    )
    parser.add_argument("--model", default=EMBEDDING_MODEL_NAME)
    parser.add_argument("--hybrid-pipeline", default=NO_MSC_HYBRID_PIPELINE_NAME)
    parser.add_argument("--create-hybrid-pipeline", action="store_true")
    parser.add_argument("--bm25-weight", type=float, default=0.5)
    parser.add_argument("--dense-weight", type=float, default=0.5)
    parser.add_argument(
        "--dense-k",
        type=int,
        default=None,
        help="Candidate count for dense retrieval before hybrid fusion. Defaults to max(top-k, 50).",
    )
    parser.add_argument("--host", default=OPENSEARCH_HOST)
    parser.add_argument("--port", type=int, default=OPENSEARCH_PORT)
    parser.add_argument("--user", default=OPENSEARCH_USER)
    parser.add_argument("--password", default=OPENSEARCH_PASSWORD)
    parser.add_argument("--no-ssl", action="store_true")
    parser.add_argument("--verify-certs", action="store_true", default=OPENSEARCH_VERIFY_CERTS)

    args = parser.parse_args()
    if args.title or args.venue or args.abstract:
        query_text = text_for_no_msc_embedding(
            {
                "title": args.title,
                "venue": args.venue,
                "abstract": args.abstract,
            }
        )
    elif args.query:
        query_text = args.query
    else:
        parser.error("provide either query text or at least one of --title, --venue, --abstract")

    client = load_opensearch_client(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        use_ssl=OPENSEARCH_USE_SSL and not args.no_ssl,
        verify_certs=args.verify_certs,
    )

    if args.create_hybrid_pipeline:
        # Creates or updates the OpenSearch-side fusion pipeline before
        # searching. It only needs to be run again when weights change.
        create_hybrid_search_pipeline(
            client=client,
            pipeline_name=args.hybrid_pipeline,
            bm25_weight=args.bm25_weight,
            dense_weight=args.dense_weight,
        )

    if args.mode == "keyword":
        response = keyword_search(
            client=client,
            index_name=args.index_name,
            query_text=query_text,
            top_k=args.top_k,
            source_fields=SOURCE_FIELDS,
        )
    elif args.mode == "vector":
        model = load_embedding_model(args.model)
        query_embedding = model.encode(
            query_text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        response = vector_search(
            client=client,
            index_name=args.index_name,
            query_embedding=query_embedding,
            top_k=args.top_k,
            source_fields=SOURCE_FIELDS,
        )
    else:
        model = load_embedding_model(args.model)
        # Hybrid mode sends the same query text to BM25 and an embedding of
        # that text to kNN; OpenSearch fuses both branches through the pipeline.
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
            dense_k=args.dense_k,
        )

    print_hits(response)


if __name__ == "__main__":
    main()
