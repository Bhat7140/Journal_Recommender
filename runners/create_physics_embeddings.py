import argparse

from configs.embedding_config import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_OUTPUT_ROOT,
    EMBEDDING_SCENARIOS,
)
from runners.embedding_common import resolve_embedding_paths, run_embedding_job


def text_for_physics_embedding(record):
    title = record.get("title") or ""
    venue = record.get("venue") or ""
    abstract = record.get("abstract") or ""
    subjects = " ".join(record.get("subjects") or [])

    parts = [
        f"Title: {title}",
        f"Subjects: {subjects}",
        f"Venue: {venue}",
        f"Abstract: {abstract}",
    ]

    return "\n".join(part for part in parts if part.split(": ", 1)[-1]).strip()


def main():
    parser = argparse.ArgumentParser(
        description="Create MiniLM embeddings for physics records."
    )
    parser.add_argument(
        "--scenario",
        choices=["physics_raw", "physics_clean"],
        default="physics_clean",
        help="Preset embedding scenario from configs.embedding_config.",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Input physics JSONL file to embed.",
    )
    parser.add_argument(
        "--run-name",
        help="Output experiment folder name. Defaults to the input filename.",
    )
    parser.add_argument(
        "--output-dir",
        help="Output folder for works.jsonl, embeddings.npy, and metadata.",
    )
    parser.add_argument(
        "--model",
        default=EMBEDDING_MODEL_NAME,
        help="SentenceTransformer model used for embeddings.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=EMBEDDING_BATCH_SIZE,
        help="Batch size for transformer encoding.",
    )

    args = parser.parse_args()
    if args.input:
        args.scenario = None

    input_path, output_dir, run_name = resolve_embedding_paths(
        args=args,
        scenarios=EMBEDDING_SCENARIOS,
        default_output_dir=EMBEDDING_OUTPUT_ROOT / "physics",
    )

    run_embedding_job(
        input_path=input_path,
        output_dir=output_dir,
        run_name=run_name,
        model_name=args.model,
        batch_size=args.batch_size,
        text_builder=text_for_physics_embedding,
        text_fields=["title", "subjects", "venue", "abstract"],
        embedding_type="physics",
    )


if __name__ == "__main__":
    main()
