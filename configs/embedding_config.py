from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_BATCH_SIZE = 32
EMBEDDING_OUTPUT_ROOT = BASE_DIR / "output" / "embeddings" / "all_minilm_l6_v2"

EMBEDDING_SCENARIOS = {
    "no_msc_raw": {
        "input_path": BASE_DIR / "output" / "no_msc" / "raw.jsonl",
        "output_dir": EMBEDDING_OUTPUT_ROOT / "no_msc_raw",
    },
    "no_msc_clean": {
        "input_path": BASE_DIR / "output" / "no_msc" / "clean.jsonl",
        "output_dir": EMBEDDING_OUTPUT_ROOT / "no_msc_clean",
    },
    "msc_raw": {
        "input_path": BASE_DIR / "output" / "msc" / "raw.jsonl",
        "output_dir": EMBEDDING_OUTPUT_ROOT / "msc_raw",
    },
    "msc_clean": {
        "input_path": BASE_DIR / "output" / "msc" / "clean.jsonl",
        "output_dir": EMBEDDING_OUTPUT_ROOT / "msc_clean",
    },

}
