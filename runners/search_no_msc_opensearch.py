import argparse

from configs.embedding_config import EMBEDDING_MODEL_NAME
from configs.opensearch_config import (
    NO_MSC_INDEX_NAME,
    OPENSEARCH_HOST,
    OPENSEARCH_PASSWORD,
    OPENSEARCH_PORT,
    OPENSEARCH_USE_SSL,
    OPENSEARCH_USER,
    OPENSEARCH_VERIFY_CERTS,
)
from runners.embedding_common import load_embedding_model
from search_backends.opensearch_backend import (
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
    parser.add_argument("query")
    parser.add_argument("--index-name", default=NO_MSC_INDEX_NAME)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument(
        "--mode",
        choices=["vector", "keyword"],
        default="vector",
        help="Use vector search or BM25 keyword search.",
    )
    parser.add_argument("--model", default=EMBEDDING_MODEL_NAME)
    parser.add_argument("--host", default=OPENSEARCH_HOST)
    parser.add_argument("--port", type=int, default=OPENSEARCH_PORT)
    parser.add_argument("--user", default=OPENSEARCH_USER)
    parser.add_argument("--password", default=OPENSEARCH_PASSWORD)
    parser.add_argument("--no-ssl", action="store_true")
    parser.add_argument("--verify-certs", action="store_true", default=OPENSEARCH_VERIFY_CERTS)

    args = parser.parse_args()
    client = load_opensearch_client(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        use_ssl=OPENSEARCH_USE_SSL and not args.no_ssl,
        verify_certs=args.verify_certs,
    )

    if args.mode == "keyword":
        response = keyword_search(
            client=client,
            index_name=args.index_name,
            query_text=args.query,
            top_k=args.top_k,
            source_fields=SOURCE_FIELDS,
        )
    else:
        model = load_embedding_model(args.model)
        query_embedding = model.encode(
            args.query,
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

    print_hits(response)


if __name__ == "__main__":
    main()
