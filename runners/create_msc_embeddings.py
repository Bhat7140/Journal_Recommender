import argparse
from pathlib import Path

from configs.embedding_config import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_OUTPUT_ROOT,
)
from configs.msc_code_descriptions import MSC_CODE_DESCRIPTIONS
from runners.embedding_common import run_embedding_job, safe_run_name


def top_level_msc_code(subject):
    code = str(subject).replace("msc:", "").strip()
    return code[:2] if len(code) >= 2 else None


def msc_description_text(subjects):
    descriptions = []

    for subject in subjects or []:
        top_code = top_level_msc_code(subject)
        description = MSC_CODE_DESCRIPTIONS.get(top_code)

        if description:
            descriptions.append(f"{subject}: {description}")

    return "; ".join(dict.fromkeys(descriptions))


def text_for_msc_embedding(record):
    title = record.get("title") or ""
    venue = record.get("venue") or ""
    abstract = record.get("abstract") or ""
    subjects = record.get("subjects") or []
    subject_codes = " ".join(subjects)
    subject_descriptions = msc_description_text(subjects)

    parts = [
        f"Title: {title}",
        f"MSC codes: {subject_codes}",
        f"MSC descriptions: {subject_descriptions}",
        f"Venue: {venue}",
        f"Abstract: {abstract}",
    ]

    return "\n".join(part for part in parts if part.split(": ", 1)[-1]).strip()


def main():
    parser = argparse.ArgumentParser(
        description="Create MiniLM embeddings with MSC code descriptions."
    )
    parser.add_argument(
        "--input",
        default="output/msc/clean.jsonl",
        # Put the MSC JSONL file you want here, for example:
        # --input output/msc/raw.jsonl
        help="Input MSC JSONL file to embed.",
    )
    parser.add_argument(
        "--run-name",
        # Put the experiment name here, for example:
        # --run-name msc_clean
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
    output_dir = Path(args.output_dir) if args.output_dir else EMBEDDING_OUTPUT_ROOT / "msc" / run_name

    run_embedding_job(
        input_path=input_path,
        output_dir=output_dir,
        run_name=run_name,
        model_name=args.model,
        batch_size=args.batch_size,
        text_builder=text_for_msc_embedding,
        text_fields=[
            "title",
            "subjects",
            "msc_code_descriptions",
            "venue",
            "abstract",
        ],
        embedding_type="msc_with_descriptions",
    )


if __name__ == "__main__":
    main()
