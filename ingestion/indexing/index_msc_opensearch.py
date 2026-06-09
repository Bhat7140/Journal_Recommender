import argparse

from configs.opensearch_config import (
    MSC_EMBEDDING_DIR,
    MSC_INDEX_NAME,
    OPENSEARCH_BULK_CHUNK_SIZE,
    OPENSEARCH_HOST,
    OPENSEARCH_PASSWORD,
    OPENSEARCH_PORT,
    OPENSEARCH_USE_SSL,
    OPENSEARCH_USER,
    OPENSEARCH_VERIFY_CERTS,
)
from core.search.opensearch_backend import bulk_index_embeddings, load_opensearch_client


def main():
    parser = argparse.ArgumentParser(
        description="Index MSC-aware works and embeddings into local OpenSearch."
    )
    parser.add_argument("--index-name", default=MSC_INDEX_NAME)
    parser.add_argument("--embedding-dir", default=MSC_EMBEDDING_DIR)
    parser.add_argument("--host", default=OPENSEARCH_HOST)
    parser.add_argument("--port", type=int, default=OPENSEARCH_PORT)
    parser.add_argument("--user", default=OPENSEARCH_USER)
    parser.add_argument("--password", default=OPENSEARCH_PASSWORD)
    parser.add_argument("--no-ssl", action="store_true")
    parser.add_argument("--verify-certs", action="store_true", default=OPENSEARCH_VERIFY_CERTS)
    parser.add_argument("--chunk-size", type=int, default=OPENSEARCH_BULK_CHUNK_SIZE)
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and rebuild the index if it already exists.",
    )

    args = parser.parse_args()
    client = load_opensearch_client(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        use_ssl=OPENSEARCH_USE_SSL and not args.no_ssl,
        verify_certs=args.verify_certs,
    )

    result = bulk_index_embeddings(
        client=client,
        index_name=args.index_name,
        embedding_dir=args.embedding_dir,
        chunk_size=args.chunk_size,
        recreate=args.recreate,
    )

    print("[DONE] OpenSearch MSC index")
    print(f"  index name : {result['index_name']}")
    print(f"  run name   : {result['run_name']}")
    print(f"  records    : {result['records']}")
    print(f"  indexed    : {result['indexed']}")
    print(f"  dimension  : {result['dimension']}")
    print(f"  errors     : {len(result['errors'])}")


if __name__ == "__main__":
    main()
