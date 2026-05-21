from configs.embedding_config import BASE_DIR


OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200
OPENSEARCH_USER = "admin"
OPENSEARCH_PASSWORD = "admin"
OPENSEARCH_USE_SSL = False
OPENSEARCH_VERIFY_CERTS = False

NO_MSC_INDEX_NAME = "journal_recommender_no_msc"
NO_MSC_EMBEDDING_DIR = BASE_DIR / "output" / "embeddings" / "no_msc_clean"

OPENSEARCH_BULK_CHUNK_SIZE = 500
