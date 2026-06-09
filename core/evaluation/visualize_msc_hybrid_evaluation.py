import argparse
from pathlib import Path

from configs.embedding_config import BASE_DIR
from core.evaluation.visualize_no_msc_hybrid_evaluation import read_csv, write_report


def main():
    parser = argparse.ArgumentParser(
        description="Create HTML/SVG visualizations for MSC hybrid evaluation results."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=BASE_DIR / "output" / "opensearch_evaluation_msc",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE_DIR
        / "output"
        / "opensearch_evaluation_msc"
        / "hybrid_evaluation_report.html",
    )
    args = parser.parse_args()

    summary_rows = read_csv(args.input_dir / "summary.csv")
    rows_by_scenario = {
        row["scenario"]: read_csv(args.input_dir / f"{row['scenario']}_details.csv")
        for row in summary_rows
    }

    write_report(
        output_path=args.output,
        summary_rows=summary_rows,
        rows_by_scenario=rows_by_scenario,
        report_title="MSC Hybrid Evaluation",
        description=(
            "Evaluation uses leave-one-out retrieval with shared MSC-code "
            "relevance. By default, relevance is shared top-level MSC class."
        ),
    )
    print("[DONE] MSC hybrid evaluation visualizations")
    print(f"  report : {args.output}")


if __name__ == "__main__":
    main()
