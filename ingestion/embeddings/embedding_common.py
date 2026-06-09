import json
from pathlib import Path

import numpy as np


def load_jsonl(path):
    records = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    return records


def write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_embedding_model(model_name):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is required for all-MiniLM-L6-v2 embeddings. "
            "Install it with: pip install sentence-transformers"
        ) from exc

    model = SentenceTransformer(model_name)
    model.max_seq_length = 256

    return model


def create_embeddings(model, texts, batch_size):
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    return embeddings.astype(np.float32)


def write_embedding_metadata(
    path,
    run_name,
    input_path,
    model_name,
    embeddings,
    text_fields,
    embedding_type,
):
    metadata = {
        "run_name": run_name,
        "embedding_type": embedding_type,
        "input_path": str(input_path),
        "model_name": model_name,
        "embedding_shape": list(embeddings.shape),
        "normalized": True,
        "text_fields": text_fields,
        "output_files": ["works.jsonl", "embeddings.npy", "embedding_metadata.json"],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        f.write("\n")


def safe_run_name(input_path):
    name = Path(input_path).stem.lower()
    return "".join(char if char.isalnum() else "_" for char in name).strip("_")


def resolve_embedding_paths(args, scenarios, default_output_dir):
    if args.scenario:
        scenario = scenarios[args.scenario]
        input_path = Path(scenario["input_path"])
        output_dir = Path(args.output_dir) if args.output_dir else Path(scenario["output_dir"])
        run_name = args.run_name or args.scenario
    else:
        input_path = Path(args.input)
        run_name = args.run_name or safe_run_name(input_path)
        output_dir = Path(args.output_dir) if args.output_dir else default_output_dir / run_name

    return input_path, output_dir, run_name


def run_embedding_job(
    input_path,
    output_dir,
    run_name,
    model_name,
    batch_size,
    text_builder,
    text_fields,
    embedding_type,
):
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Missing input file: {input_path}")

    records = load_jsonl(input_path)
    usable_records = []
    texts = []

    for record in records:
        text = text_builder(record)
        if text:
            usable_records.append(record)
            texts.append(text)

    if not usable_records:
        raise ValueError(f"No usable records found in {input_path}")

    model = load_embedding_model(model_name)
    embeddings = create_embeddings(model, texts, batch_size)

    output_dir.mkdir(parents=True, exist_ok=True)

    works_path = output_dir / "works.jsonl"
    embeddings_path = output_dir / "embeddings.npy"
    metadata_path = output_dir / "embedding_metadata.json"

    write_jsonl(works_path, usable_records)
    np.save(embeddings_path, embeddings)
    write_embedding_metadata(
        metadata_path,
        run_name,
        input_path,
        model_name,
        embeddings,
        text_fields,
        embedding_type,
    )

    print(f"[DONE] {run_name}")
    print(f"  embedding type   : {embedding_type}")
    print(f"  input records    : {len(records)}")
    print(f"  embedded records : {len(usable_records)}")
    print(f"  embedding shape  : {embeddings.shape}")
    print(f"  works path       : {works_path}")
    print(f"  embeddings path  : {embeddings_path}")
    print(f"  metadata path    : {metadata_path}")
