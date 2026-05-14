import json
import numpy as np
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity


class RetrievalEvaluator:
    def __init__(self, works_path, embeddings_path):
        """
        works_path:
            JSONL file containing metadata

        embeddings_path:
            .npy file containing embeddings
        """

        self.works = self.load_jsonl(works_path)
        self.embeddings = np.load(embeddings_path)

        if len(self.works) != len(self.embeddings):
            raise ValueError(
                f"Mismatch between works ({len(self.works)}) "
                f"and embeddings ({len(self.embeddings)})"
            )

    @staticmethod
    def load_jsonl(path):
        data = []

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                data.append(json.loads(line))

        return data

    def cosine(self, idx1, idx2):
        vec1 = self.embeddings[idx1].reshape(1, -1)
        vec2 = self.embeddings[idx2].reshape(1, -1)

        return cosine_similarity(vec1, vec2)[0][0]

    def evaluate_msc_alignment(self):
        """
        Compare similarity:
        - same MSC
        - different MSC
        """

        same_scores = []
        diff_scores = []

        for i in range(len(self.works)):
            msc_i = set(self.works[i].get("msc_codes", []))

            for j in range(i + 1, len(self.works)):
                msc_j = set(self.works[j].get("msc_codes", []))

                sim = self.cosine(i, j)

                if msc_i & msc_j:
                    same_scores.append(sim)
                else:
                    diff_scores.append(sim)

        same_avg = np.mean(same_scores) if same_scores else 0
        diff_avg = np.mean(diff_scores) if diff_scores else 0

        print("\n=== MSC ALIGNMENT EVALUATION ===")
        print(f"Average SAME MSC similarity     : {same_avg:.4f}")
        print(f"Average DIFFERENT MSC similarity: {diff_avg:.4f}")

        separation = same_avg - diff_avg
        print(f"Separation score                : {separation:.4f}")

    def get_top_k_neighbors(self, index, k=5):
        """
        Retrieve nearest neighbors for a paper
        """

        query_vec = self.embeddings[index].reshape(1, -1)

        similarities = cosine_similarity(query_vec, self.embeddings)[0]

        ranked_indices = np.argsort(similarities)[::-1]

        neighbors = []

        for idx in ranked_indices:
            if idx == index:
                continue

            neighbors.append(
                {
                    "index": idx,
                    "score": float(similarities[idx]),
                    "title": self.works[idx].get("title", ""),
                    "msc_codes": self.works[idx].get("msc_codes", []),
                }
            )

            if len(neighbors) >= k:
                break

        return neighbors

    def inspect_neighbors(self, index, k=5):
        """
        Human-readable neighbor inspection
        """

        work = self.works[index]

        print("\n" + "=" * 80)
        print("QUERY PAPER")
        print("=" * 80)

        print(f"Title     : {work.get('title')}")
        print(f"MSC Codes : {work.get('msc_codes')}")

        print("\nTOP NEIGHBORS\n")

        neighbors = self.get_top_k_neighbors(index, k)

        for i, neighbor in enumerate(neighbors, start=1):
            print(f"[{i}] Score: {neighbor['score']:.4f}")
            print(f"Title    : {neighbor['title']}")
            print(f"MSC      : {neighbor['msc_codes']}")
            print("-" * 80)