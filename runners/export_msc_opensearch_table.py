import argparse
from pathlib import Path

from configs.embedding_config import BASE_DIR
from configs.opensearch_config import (
    MSC_INDEX_NAME,
    OPENSEARCH_HOST,
    OPENSEARCH_PASSWORD,
    OPENSEARCH_PORT,
    OPENSEARCH_USE_SSL,
    OPENSEARCH_USER,
    OPENSEARCH_VERIFY_CERTS,
)
from runners.export_no_msc_opensearch_table import (
    fetch_documents,
    write_csv,
    write_html,
)
from search_backends.opensearch_backend import load_opensearch_client


def main():
    parser = argparse.ArgumentParser(
        description="Export a readable table preview of the MSC OpenSearch index."
    )
    parser.add_argument("--index-name", default=MSC_INDEX_NAME)
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--host", default=OPENSEARCH_HOST)
    parser.add_argument("--port", type=int, default=OPENSEARCH_PORT)
    parser.add_argument("--user", default=OPENSEARCH_USER)
    parser.add_argument("--password", default=OPENSEARCH_PASSWORD)
    parser.add_argument("--no-ssl", action="store_true")
    parser.add_argument("--verify-certs", action="store_true", default=OPENSEARCH_VERIFY_CERTS)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BASE_DIR / "output" / "opensearch_preview",
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

    rows = fetch_documents(client, args.index_name, args.size)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = args.output_dir / f"{args.index_name}.csv"
    html_path = args.output_dir / f"{args.index_name}.html"
    write_csv(rows, csv_path)
    write_html(rows, html_path, args.index_name)

    print("[DONE] Exported MSC OpenSearch preview")
    print(f"  documents : {len(rows)}")
    print(f"  csv       : {csv_path}")
    print(f"  html      : {html_path}")


if __name__ == "__main__":
    main()
