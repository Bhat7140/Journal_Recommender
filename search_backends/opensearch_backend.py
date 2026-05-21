import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np


def load_opensearch_client(
    host: str,
    port: int,
    user: str,
    password: str,
    use_ssl: bool,
    verify_certs: bool,
):
    try:
        from opensearchpy import OpenSearch
    except ImportError as exc:
        raise ImportError(
            "opensearch-py is required for OpenSearch indexing/search. "
            "Install it with: pip install opensearch-py"
        ) from exc

    return OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=(user, password),
        use_ssl=use_ssl,
        verify_certs=verify_certs,
        ssl_show_warn=verify_certs,
    )


def load_jsonl(path: Path) -> List[Dict]:
    records = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    return records


def stable_work_id(record: Dict) -> str:
    if record.get("doi"):
        return str(record["doi"]).lower()

    fallback = f"{record.get('title') or ''}|{record.get('year') or ''}"
    return hashlib.sha1(fallback.encode("utf-8")).hexdigest()


def stable_embedding_id(work_id: str, run_name: str) -> str:
    return hashlib.sha1(f"{run_name}|{work_id}".encode("utf-8")).hexdigest()


def create_no_msc_index(
    client,
    index_name: str,
    dimension: int,
    metadata: Optional[Dict] = None,
    recreate: bool = False,
):
    if client.indices.exists(index=index_name):
        if not recreate:
            return
        client.indices.delete(index=index_name)

    body = {
        "settings": {
            "index": {
                "knn": True,
                "number_of_shards": 1,
                "number_of_replicas": 0,
            }
        },
        "mappings": {
            "_meta": metadata or {},
            "properties": {
                "work_id": {"type": "keyword"},
                "embedding_id": {"type": "keyword"},
                "embedding_run": {"type": "keyword"},
                "embedding_index": {"type": "integer"},
                "doi": {"type": "keyword"},
                "title": {"type": "text"},
                "abstract": {"type": "text"},
                "year": {"type": "integer"},
                "authors": {"type": "keyword"},
                "venue": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "subjects": {"type": "keyword"},
                "issn": {"type": "keyword"},
                "source": {
                    "properties": {
                        "zbmath": {"type": "boolean"},
                        "crossref": {"type": "boolean"},
                        "openalex": {"type": "boolean"},
                    }
                },
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dimension,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "lucene",
                    },
                },
            },
        },
    }

    client.indices.create(index=index_name, body=body)


def iter_index_actions(
    index_name: str,
    records: List[Dict],
    embeddings: np.ndarray,
    run_name: str,
) -> Iterable[Dict]:
    for embedding_index, (record, embedding) in enumerate(zip(records, embeddings)):
        work_id = stable_work_id(record)
        embedding_id = stable_embedding_id(work_id, run_name)

        yield {
            "_index": index_name,
            "_id": work_id,
            "_source": {
                "work_id": work_id,
                "embedding_id": embedding_id,
                "embedding_run": run_name,
                "embedding_index": embedding_index,
                "doi": record.get("doi"),
                "title": record.get("title"),
                "abstract": record.get("abstract"),
                "year": record.get("year"),
                "authors": record.get("authors") or [],
                "venue": record.get("venue"),
                "subjects": record.get("subjects") or [],
                "issn": record.get("issn") or [],
                "source": record.get("source") or {},
                "embedding": embedding.astype(float).tolist(),
            },
        }


def bulk_index_no_msc(
    client,
    index_name: str,
    embedding_dir: Path,
    chunk_size: int,
    recreate: bool = False,
):
    try:
        from opensearchpy import helpers
    except ImportError as exc:
        raise ImportError(
            "opensearch-py is required for OpenSearch indexing/search. "
            "Install it with: pip install opensearch-py"
        ) from exc

    embedding_dir = Path(embedding_dir)
    works_path = embedding_dir / "works.jsonl"
    embeddings_path = embedding_dir / "embeddings.npy"
    metadata_path = embedding_dir / "embedding_metadata.json"

    records = load_jsonl(works_path)
    embeddings = np.load(embeddings_path)

    if len(records) != len(embeddings):
        raise ValueError(
            f"Record/vector count mismatch: {len(records)} records, "
            f"{len(embeddings)} embeddings"
        )

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    run_name = metadata.get("run_name") or embedding_dir.name
    dimension = int(embeddings.shape[1])
    create_no_msc_index(
        client=client,
        index_name=index_name,
        dimension=dimension,
        metadata=metadata,
        recreate=recreate,
    )

    success, errors = helpers.bulk(
        client,
        iter_index_actions(index_name, records, embeddings, run_name),
        chunk_size=chunk_size,
        raise_on_error=False,
    )
    client.indices.refresh(index=index_name)

    return {
        "indexed": success,
        "errors": errors,
        "records": len(records),
        "dimension": dimension,
        "run_name": run_name,
        "index_name": index_name,
    }


def vector_search(
    client,
    index_name: str,
    query_embedding: np.ndarray,
    top_k: int,
    source_fields: Optional[List[str]] = None,
):
    if query_embedding.ndim != 1:
        raise ValueError("query_embedding must be a single vector")
    vector = query_embedding.astype(float).tolist()

    body = {
        "size": top_k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": vector,
                    "k": top_k,
                }
            }
        },
    }

    if source_fields is not None:
        body["_source"] = source_fields

    return client.search(index=index_name, body=body)


def keyword_search(
    client,
    index_name: str,
    query_text: str,
    top_k: int,
    source_fields: Optional[List[str]] = None,
):
    body = {
        "size": top_k,
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": ["title^3", "abstract", "venue^2", "authors"],
            }
        },
    }

    if source_fields is not None:
        body["_source"] = source_fields

    return client.search(index=index_name, body=body)


def get_by_work_id(client, index_name: str, work_id: str):
    return client.get(index=index_name, id=work_id)


def get_by_embedding_id(client, index_name: str, embedding_id: str):
    body = {
        "size": 1,
        "query": {
            "term": {
                "embedding_id": embedding_id,
            }
        },
    }

    return client.search(index=index_name, body=body)
