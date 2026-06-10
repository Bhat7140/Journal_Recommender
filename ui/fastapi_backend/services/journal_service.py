import sys
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from configs.embedding_config import EMBEDDING_MODEL_NAME
from configs.opensearch_config import (
    MSC_EMBEDDING_DIR,
    MSC_HYBRID_PIPELINE_NAME,
    MSC_INDEX_NAME,
    OPENSEARCH_BULK_CHUNK_SIZE,
    OPENSEARCH_HOST,
    OPENSEARCH_PASSWORD,
    OPENSEARCH_PORT,
    OPENSEARCH_USE_SSL,
    OPENSEARCH_USER,
    OPENSEARCH_VERIFY_CERTS,
    PHYSICS_EMBEDDING_DIR,
    PHYSICS_HYBRID_PIPELINE_NAME,
    PHYSICS_INDEX_NAME,
)
from core.search.opensearch_backend import (
    DEFAULT_HYBRID_FIELDS,
    MSC_HYBRID_FIELDS,
    bulk_index_embeddings,
    create_hybrid_search_pipeline,
    hybrid_search,
    load_opensearch_client,
)
from ingestion.embeddings.create_msc_embeddings import text_for_msc_embedding
from ingestion.embeddings.create_physics_embeddings import text_for_physics_embedding
from ingestion.embeddings.embedding_common import load_embedding_model


SOURCE_FIELDS = [
    "title",
    "year",
    "authors",
    "journal_name",
    "venue",
    "issn",
    "doi",
    "abstract",
    "subjects",
]

DOMAIN_CONFIGS = {
    "mathematics": {
        "index_name": MSC_INDEX_NAME,
        "embedding_dir": MSC_EMBEDDING_DIR,
        "pipeline_name": MSC_HYBRID_PIPELINE_NAME,
        "lexical_fields": MSC_HYBRID_FIELDS,
        "text_builder": text_for_msc_embedding,
    },
    "physics": {
        "index_name": PHYSICS_INDEX_NAME,
        "embedding_dir": PHYSICS_EMBEDDING_DIR,
        "pipeline_name": PHYSICS_HYBRID_PIPELINE_NAME,
        "lexical_fields": DEFAULT_HYBRID_FIELDS,
        "text_builder": text_for_physics_embedding,
    },
}

LAST_RECOMMENDATIONS_BY_JOURNAL = {}


@lru_cache(maxsize=1)
def get_client():
    return load_opensearch_client(
        host=OPENSEARCH_HOST,
        port=OPENSEARCH_PORT,
        user=OPENSEARCH_USER,
        password=OPENSEARCH_PASSWORD,
        use_ssl=OPENSEARCH_USE_SSL,
        verify_certs=OPENSEARCH_VERIFY_CERTS,
    )


@lru_cache(maxsize=1)
def get_model():
    return load_embedding_model(EMBEDDING_MODEL_NAME)


def selected_domains(domain):
    normalized = (domain or "all").strip().lower()
    if normalized in {"mathematics", "math", "msc"}:
        return ["mathematics"]
    if normalized in {"physics", "physcos"}:
        return ["physics"]
    return ["mathematics", "physics"]


def parse_subjects(keyword):
    if not keyword:
        return []
    return [
        subject.strip()
        for subject in keyword.replace(",", " ").split()
        if subject.strip()
    ]


def build_query_record(*, title, abstract_text, keyword, domain_key):
    record = {
        "title": title or "",
        "abstract": abstract_text or "",
        "venue": "",
        "journal_name": "",
        "subjects": [],
    }

    if domain_key == "mathematics":
        record["subjects"] = parse_subjects(keyword)
    elif keyword:
        record["subjects"] = parse_subjects(keyword)
        record["abstract"] = f"{record['abstract']}\nKeywords: {keyword}".strip()

    return record


def ensure_search_ready(client, config):
    index_name = config["index_name"]
    if not client.indices.exists(index=index_name):
        bulk_index_embeddings(
            client=client,
            index_name=index_name,
            embedding_dir=config["embedding_dir"],
            chunk_size=OPENSEARCH_BULK_CHUNK_SIZE,
            recreate=False,
        )

    create_hybrid_search_pipeline(
        client=client,
        pipeline_name=config["pipeline_name"],
        bm25_weight=0.5,
        dense_weight=0.5,
    )


def search_domain(*, title, abstract_text, keyword, domain_key, top_k=50):
    client = get_client()
    model = get_model()
    config = DOMAIN_CONFIGS[domain_key]
    ensure_search_ready(client, config)

    query_record = build_query_record(
        title=title,
        abstract_text=abstract_text,
        keyword=keyword,
        domain_key=domain_key,
    )
    query_text = config["text_builder"](query_record)
    query_embedding = model.encode(
        query_text,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    response = hybrid_search(
        client=client,
        index_name=config["index_name"],
        query_text=query_text,
        query_embedding=query_embedding,
        top_k=top_k,
        search_pipeline=config["pipeline_name"],
        source_fields=SOURCE_FIELDS,
        lexical_fields=config["lexical_fields"],
        dense_k=max(top_k, 100),
    )

    return response["hits"]["hits"]


def journal_key(source):
    return source.get("journal_name") or source.get("venue") or "Unknown journal"


def confidence_for_score(score_percent):
    if score_percent >= 75:
        return "high"
    if score_percent >= 45:
        return "medium"
    return "low"


def make_reason(journal_name, best_paper, domain_label):
    title = best_paper.get("title") or "the top supporting paper"
    return (
        f"{journal_name} is ranked highly for this {domain_label} manuscript "
        f"because OpenSearch found strong hybrid similarity to \"{title}\"."
    )


def group_hits_by_journal(hits, domain_label):
    groups = {}
    for hit in hits:
        source = hit.get("_source", {})
        key = journal_key(source)
        group = groups.setdefault(
            key,
            {
                "journal_name": key,
                "issn": source.get("issn") or [],
                "domain": domain_label,
                "hits": [],
            },
        )
        if not group["issn"] and source.get("issn"):
            group["issn"] = source.get("issn")
        group["hits"].append(
            {
                "title": source.get("title") or "(untitled)",
                "year": source.get("year") or 0,
                "doi": source.get("doi") or "",
                "hybrid_score": float(hit.get("_score") or 0.0),
            }
        )

    return list(groups.values())


def format_recommendations(groups):
    groups.sort(key=lambda group: max(paper["hybrid_score"] for paper in group["hits"]), reverse=True)
    top_score = max(
        (paper["hybrid_score"] for group in groups for paper in group["hits"]),
        default=1.0,
    ) or 1.0

    recommendations = []
    for rank, group in enumerate(groups[:10], start=1):
        supporting_papers = sorted(
            group["hits"],
            key=lambda paper: paper["hybrid_score"],
            reverse=True,
        )[:5]
        best_paper = supporting_papers[0]
        score_percent = round(max(0.0, min(1.0, best_paper["hybrid_score"] / top_score)) * 100)
        journal_name = group["journal_name"]
        recommendations.append(
            {
                "journal_name": journal_name,
                "issn": group["issn"],
                "match_score_percent": score_percent,
                "confidence": confidence_for_score(score_percent),
                "reason": make_reason(journal_name, best_paper, group["domain"]),
                "supporting_paper_count": len(group["hits"]),
                "best_matching_paper": best_paper,
                "supporting_papers": supporting_papers,
                "rank": rank,
            }
        )

    return recommendations


def get_journals(
    *,
    title: str = "",
    abstract_text: str = "",
    references: str = "",
    domain: str = "all",
    open_access_only: bool = False,
    keyword: str = "",
    sort_by: str = "match",
) -> dict:
    del references, open_access_only, sort_by

    hits = []
    for domain_key in selected_domains(domain):
        hits.extend(
            search_domain(
                title=title,
                abstract_text=abstract_text,
                keyword=keyword,
                domain_key=domain_key,
            )
        )

    groups = []
    for domain_key in selected_domains(domain):
        domain_hits = [
            hit
            for hit in hits
            if hit.get("_index") == DOMAIN_CONFIGS[domain_key]["index_name"]
        ]
        groups.extend(group_hits_by_journal(domain_hits, domain_key))

    recommendations = format_recommendations(groups)
    LAST_RECOMMENDATIONS_BY_JOURNAL.clear()
    LAST_RECOMMENDATIONS_BY_JOURNAL.update(
        {recommendation["journal_name"]: recommendation for recommendation in recommendations}
    )

    return {
        "query": {
            "title": title,
            "abstract": abstract_text,
        },
        "recommendations": recommendations,
    }


def get_journal_by_id(journal_id: str) -> dict | None:
    return LAST_RECOMMENDATIONS_BY_JOURNAL.get(journal_id)
