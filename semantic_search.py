import json
import numpy as np
from sentence_transformers import SentenceTransformer


def load_jsonl(path: str):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


class SemanticSearcher:
    def __init__(
            self,
            model_name: str,
            embeddings_path: str,
            records_path: str,
    ) -> None:
        self.model = SentenceTransformer(model_name)
        self.embeddings = np.load(embeddings_path)
        self.records = load_jsonl(records_path)

        if len(self.records) != len(self.embeddings):
            raise ValueError("Mismatch between embeddings and record count")

    def search(self, query: str, top_k: int = 5):
        query_vec = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0].astype("float32")

        # cosine similarity because vectors were normalized
        scores = self.embeddings @ query_vec
        top_idx = np.argsort(-scores)[:top_k]

        results = []
        for idx in top_idx:
            rec = self.records[int(idx)]
            results.append(
                {
                    "score": float(scores[idx]),
                    "record_id": rec["record_id"],
                    "doi": rec.get("doi"),
                    "title": rec.get("title"),
                    "venue": rec.get("venue"),
                    "year": rec.get("year"),
                }
            )
        return results


if __name__ == "__main__":
    searcher = SemanticSearcher(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        embeddings_path="semantic_index_data/embeddings.npy",
        records_path="semantic_index_data/embedding_records.jsonl",
    )

    query = "papers on algebraic topology and homotopy groups"
    results = searcher.search(query, top_k=5)

    for r in results:
        print("-" * 80)
        print(f"Score: {r['score']:.4f}")
        print(f"Title: {r['title']}")
        print(f"DOI: {r['doi']}")
        print(f"Venue: {r['venue']}")
        print(f"Year: {r['year']}")