from configs.embedding_config import BASE_DIR


OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200
OPENSEARCH_USER = "admin"
OPENSEARCH_PASSWORD = "admin"
OPENSEARCH_USE_SSL = False
OPENSEARCH_VERIFY_CERTS = False

NO_MSC_INDEX_NAME = "journal_recommender_no_msc"
NO_MSC_EMBEDDING_DIR = BASE_DIR / "output" / "embeddings" / "no_msc_clean"
# Search pipeline used to fuse BM25 metadata matches with dense vector matches.
NO_MSC_HYBRID_PIPELINE_NAME = "journal_recommender_no_msc_hybrid"

MSC_INDEX_NAME = "journal_recommender_msc"
MSC_EMBEDDING_DIR = BASE_DIR / "output" / "embeddings" / "msc_clean"
# Search pipeline used to fuse MSC-aware BM25 matches with dense vector matches.
MSC_HYBRID_PIPELINE_NAME = "journal_recommender_msc_hybrid"

OPENSEARCH_BULK_CHUNK_SIZE = 500
