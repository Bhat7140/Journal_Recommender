from retrieval_eval import RetrievalEvaluator


def main():

    evaluator = RetrievalEvaluator(
        works_path="../output/msc/works.jsonl",
        embeddings_path="../output/msc/embeddings.npy",
    )

    # -----------------------------------
    # 1. MSC alignment check
    # -----------------------------------

    evaluator.evaluate_msc_alignment()

    # -----------------------------------
    # 2. Manual neighbor inspection
    # -----------------------------------

    sample_indices = [0, 5, 10]

    for idx in sample_indices:
        evaluator.inspect_neighbors(index=idx, k=5)


if __name__ == "__main__":
    main()