import json
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer


class MetadataEmbedder:
    """
    Reads metadata records from works.jsonl, builds semantic text per record,
    generates dense embeddings, and saves:
      - embeddings.npy
      - embedding_records.jsonl

    This is for bi-encoder semantic retrieval, not reranking.
    """

    def __init__(
            self,
            model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
            batch_size: int = 32,
            normalize_embeddings: bool = True,
            max_abstract_chars: int = 2000,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.normalize_embeddings = normalize_embeddings
        self.max_abstract_chars = max_abstract_chars
        self.model = SentenceTransformer(model_name)

    @staticmethod
    def load_jsonl(path: str) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    @staticmethod
    def get_record_id(record: Dict[str, Any], fallback_index: int) -> str:
        doi = record.get("doi")
        if doi:
            return doi
        ids = record.get("ids", {})
        openalex_id = ids.get("openalex", {}).get("id") if isinstance(ids, dict) else None
        if openalex_id:
            return openalex_id
        return f"record_{fallback_index}"

    def build_text(self, record: Dict[str, Any]) -> Optional[str]:
        """
        Create one semantic text block per paper.
        Keep it structured and not too long.
        """
        title = (record.get("title") or "").strip()
        abstract = (record.get("abstract") or "").strip()
        venue = (record.get("venue") or "").strip()
        year = record.get("year")

        if not title and not abstract:
            return None

        if abstract:
            abstract = abstract[: self.max_abstract_chars]

        parts = []

        if title:
            # Repeat title once in a labeled way to increase its influence a bit
            parts.append(f"Title: {title}")

        if abstract:
            parts.append(f"Abstract: {abstract}")

        if venue:
            parts.append(f"Journal: {venue}")

        if year:
            parts.append(f"Year: {year}")

        return "\n".join(parts)

    def prepare_documents(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        prepared: List[Dict[str, Any]] = []

        for i, record in enumerate(records):
            doc_text = self.build_text(record)
            if not doc_text:
                continue

            prepared.append(
                {
                    "record_id": self.get_record_id(record, i),
                    "doi": record.get("doi"),
                    "title": record.get("title"),
                    "venue": record.get("venue"),
                    "year": record.get("year"),
                    "text_for_embedding": doc_text,
                }
            )

        return prepared

    def encode_documents(self, documents: List[Dict[str, Any]]) -> np.ndarray:
        texts = [doc["text_for_embedding"] for doc in documents]

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=self.normalize_embeddings,
        )

        return embeddings.astype("float32")

    @staticmethod
    def save_outputs(
            embeddings: np.ndarray,
            documents: List[Dict[str, Any]],
            output_dir: str,
    ) -> None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        np.save(out / "embeddings.npy", embeddings)

        with open(out / "embedding_records.jsonl", "w", encoding="utf-8") as f:
            for doc in documents:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    def run(self, input_jsonl: str, output_dir: str = "semantic_index_data") -> None:
        print(f"Loading metadata from: {input_jsonl}")
        records = self.load_jsonl(input_jsonl)
        print(f"Loaded {len(records)} metadata records")

        documents = self.prepare_documents(records)
        print(f"Prepared {len(documents)} records for embedding")

        embeddings = self.encode_documents(documents)
        print(f"Embeddings shape: {embeddings.shape}")

        self.save_outputs(embeddings, documents, output_dir)
        print(f"Saved embeddings and record map to: {output_dir}")


if __name__ == "__main__":
    embedder = MetadataEmbedder(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        batch_size=32,
        normalize_embeddings=True,
        max_abstract_chars=2000,
    )
    embedder.run("works.jsonl", "semantic_index_data")