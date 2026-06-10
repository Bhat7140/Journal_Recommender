import argparse
import json
import random
from pathlib import Path

CONFIDENCE_LEVELS = ["high", "medium", "low"]
JOURNAL_PREFIXES = [
    "Annals of",
    "Journal of",
    "Communications in",
    "Advances in",
    "Proceedings of",
    "Memoirs of",
    "Transactions of",
    "Lecture Notes in",
]
JOURNAL_SUFFIXES = [
    "Mathematics",
    "Algebra",
    "Geometry",
    "Mathematical Physics",
    "Representation Theory",
    "Topology",
    "Lie Theory",
    "Quantum Algebra",
]
TOPIC_PHRASES = [
    "quantum groups",
    "cohomology theory",
    "representation theory",
    "Lie algebra methods",
    "homological invariants",
    "graded structures",
    "categorical symmetries",
    "quantum cohomology",
]


def build_query(title: str, abstract: str) -> dict:
    return {
        "title": title,
        "abstract": abstract,
    }


def build_issn(index: int) -> list[str]:
    base = 1000 + index
    issn_primary = f"{base:04d}-{(base * 7) % 10000:04d}"
    issn_secondary = f"{(base * 3) % 10000:04d}-{(base * 11) % 10000:04d}"
    return [issn_primary, issn_secondary]


def build_supporting_papers(index: int, journal_name: str, max_count: int) -> list[dict]:
    count = random.randint(1, max_count)
    papers = []

    for paper_index in range(count):
        topic = random.choice(TOPIC_PHRASES)
        paper_title = f"{topic.title()} in {journal_name}" if paper_index == 0 else f"{topic.title()} study {paper_index + 1}"
        papers.append(
            {
                "title": paper_title,
                "hybrid_score": round(random.uniform(0.04, 0.52), 8),
            }
        )

    return papers


def build_recommendations(count: int, max_supporting_papers: int) -> list[dict]:
    recommendations = []
    current_score = random.randint(55, 72)

    for index in range(count):
        journal_name = f"{random.choice(JOURNAL_PREFIXES)} {random.choice(JOURNAL_SUFFIXES)}"
        supporting_papers = build_supporting_papers(index + 1, journal_name, max_supporting_papers)
        confidence = (
            "high"
            if current_score >= 58
            else "medium"
            if current_score >= 30
            else "low"
        )
        best_matching_paper = {
            **supporting_papers[0],
            "year": random.randint(1970, 2024),
            "doi": f"10.{random.randint(1000,9999)}/{index + 1:04d}.{random.randint(100,999)}",
        }

        recommendations.append(
            {
                "journal_name": journal_name,
                "issn": build_issn(index + 1),
                "match_score_percent": current_score,
                "confidence": confidence if confidence in CONFIDENCE_LEVELS else "medium",
                "reason": (
                    f"The manuscript aligns with {random.choice(TOPIC_PHRASES)}, "
                    f"which is a strong theme in {journal_name}."
                ),
                "supporting_paper_count": len(supporting_papers),
                "best_matching_paper": best_matching_paper,
                "supporting_papers": supporting_papers,
                "rank": index + 1,
            }
        )

        current_score = max(1, current_score - random.randint(1, 9))

    return recommendations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a mock recommendation payload for the journal recommendation frontend."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of journal recommendations to generate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible output.",
    )
    parser.add_argument(
        "--title",
        default="Cohomology and representations of quantum groups",
        help="Query title to include in the generated payload.",
    )
    parser.add_argument(
        "--abstract",
        default=(
            "This manuscript studies cohomological methods for quantum groups and related "
            "algebraic structures. We investigate representations, homological invariants, "
            "and connections with Lie algebra cohomology."
        ),
        help="Query abstract to include in the generated payload.",
    )
    parser.add_argument(
        "--max-supporting-papers",
        type=int,
        default=3,
        help="Maximum number of supporting papers to generate per recommendation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("fastapi_backend/data/generated_frontend_recommendations.json"),
        help="Output JSON path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    payload = {
        "query": build_query(args.title, args.abstract),
        "recommendations": build_recommendations(args.count, args.max_supporting_papers),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {len(payload['recommendations'])} recommendations to {args.output}")


if __name__ == "__main__":
    main()
