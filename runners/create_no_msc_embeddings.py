import argparse
from pathlib import Path

from configs.embedding_config import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_OUTPUT_ROOT,
)
from runners.embedding_common import run_embedding_job, safe_run_name


def text_for_no_msc_embedding(record):
    title = record.get("title") or ""
    venue = record.get("venue") or ""
    abstract = record.get("abstract") or ""

    parts = [
        f"Title: {title}",
        f"Venue: {venue}",
        f"Abstract: {abstract}",
    ]

    return "\n".join(part for part in parts if part.split(": ", 1)[-1]).strip()


def main():
    parser = argparse.ArgumentParser(
        description="Create MiniLM embeddings without MSC code text."
    )
    parser.add_argument(
        "--input",
        default="output/no_msc/clean.jsonl",
        # Put the JSONL file you want here, for example:
        # --input output/no_msc/raw.jsonl
        help="Input JSONL file to embed.",
    )
    parser.add_argument(
        "--run-name",
        # Put the experiment name here, for example:
        # --run-name no_msc_clean
        help="Output experiment folder name. Defaults to the input filename.",
    )
    parser.add_argument(
        "--output-dir",
        # Optional: put a full custom output folder here.
        # Usually --run-name is enough.
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
    input_path = Path(args.input)
    run_name = args.run_name or safe_run_name(input_path)
    output_dir = Path(args.output_dir) if args.output_dir else EMBEDDING_OUTPUT_ROOT / "no_msc" / run_name

    run_embedding_job(
        input_path=input_path,
        output_dir=output_dir,
        run_name=run_name,
        model_name=args.model,
        batch_size=args.batch_size,
        text_builder=text_for_no_msc_embedding,
        text_fields=["title", "venue", "abstract"],
        embedding_type="no_msc",
    )


if __name__ == "__main__":
    main()
