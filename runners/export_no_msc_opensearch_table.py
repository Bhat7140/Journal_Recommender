import argparse
import csv
import html
from pathlib import Path

from configs.embedding_config import BASE_DIR
from configs.opensearch_config import (
    NO_MSC_INDEX_NAME,
    OPENSEARCH_HOST,
    OPENSEARCH_PASSWORD,
    OPENSEARCH_PORT,
    OPENSEARCH_USE_SSL,
    OPENSEARCH_USER,
    OPENSEARCH_VERIFY_CERTS,
)
from search_backends.opensearch_backend import load_opensearch_client


FIELDS = [
    "embedding_index",
    "title",
    "year",
    "authors",
    "journal_name",
    "venue",
    "issn",
    "doi",
    "subjects",
    "work_id",
    "embedding_id",
    "embedding_run",
    "embedding_preview",
]


def shorten(value, max_length=260):
    if value is None:
        return ""
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    elif isinstance(value, dict):
        value = str(value)
    else:
        value = str(value)

    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


def fetch_documents(client, index_name, size):
    body = {
        "size": size,
        "sort": [{"embedding_index": {"order": "asc"}}],
        "_source": [field for field in FIELDS if field != "embedding_preview"] + ["abstract", "embedding"],
        "query": {"match_all": {}},
    }
    response = client.search(index=index_name, body=body)
    rows = []
    for hit in response["hits"]["hits"]:
        row = hit["_source"]
        embedding = row.pop("embedding", None)
        if embedding:
            preview = ", ".join(f"{float(value):.4f}" for value in embedding[:8])
            row["embedding_preview"] = f"[{preview}, ...] dimension={len(embedding)}"
        else:
            row["embedding_preview"] = ""
        rows.append(row)
    return rows


def write_csv(rows, path):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS + ["abstract"])
        writer.writeheader()
        for row in rows:
            writer.writerow({field: shorten(row.get(field), 2000) for field in writer.fieldnames})


def write_html(rows, path, index_name):
    columns = FIELDS + ["abstract"]
    header_cells = "".join(f"<th>{html.escape(field)}</th>" for field in columns)
    body_rows = []

    for row in rows:
        cells = "".join(
            f"<td>{html.escape(shorten(row.get(field)))}</td>" for field in columns
        )
        body_rows.append(f"<tr>{cells}</tr>")

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>OpenSearch Preview - {html.escape(index_name)}</title>
  <style>
    body {{
      margin: 24px;
      font-family: Arial, sans-serif;
      color: #1f2937;
      background: #f8fafc;
    }}
    h1 {{
      font-size: 22px;
      margin: 0 0 6px;
    }}
    p {{
      margin: 0 0 18px;
      color: #475569;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      background: white;
      font-size: 13px;
    }}
    th, td {{
      border: 1px solid #d7dee8;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #e2e8f0;
      color: #0f172a;
      z-index: 1;
    }}
    tr:nth-child(even) {{
      background: #f8fafc;
    }}
    td {{
      max-width: 360px;
      overflow-wrap: anywhere;
    }}
  </style>
</head>
<body>
  <h1>{html.escape(index_name)}</h1>
  <p>Preview of {len(rows)} documents stored in OpenSearch. The embedding vector is hidden because it is a 384-number field.</p>
  <table>
    <thead><tr>{header_cells}</tr></thead>
    <tbody>{''.join(body_rows)}</tbody>
  </table>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Export a readable table preview of the no-MSC OpenSearch index."
    )
    parser.add_argument("--index-name", default=NO_MSC_INDEX_NAME)
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

    print("[DONE] Exported OpenSearch preview")
    print(f"  documents : {len(rows)}")
    print(f"  csv       : {csv_path}")
    print(f"  html      : {html_path}")


if __name__ == "__main__":
    main()
