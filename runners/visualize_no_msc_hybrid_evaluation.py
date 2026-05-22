import argparse
import csv
import html
from collections import Counter
from pathlib import Path

from configs.embedding_config import BASE_DIR


METRICS = ["precision@10", "recall@10", "mrr@10", "ndcg@10"]
COLORS = {
    "hybrid_50_50": "#2563eb",
    "hybrid_70_30": "#dc2626",
}


def read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def scenario_color(name):
    return COLORS.get(name, "#475569")


def svg_bar_chart(rows, metrics):
    width = 920
    height = 360
    margin_left = 78
    margin_top = 30
    chart_width = width - margin_left - 34
    chart_height = 250
    max_value = max(to_float(row[metric]) for row in rows for metric in metrics) or 1.0
    group_width = chart_width / len(metrics)
    bar_width = min(42, group_width / (len(rows) + 1.2))

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Summary metrics bar chart">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<line x1="{margin_left}" y1="{margin_top + chart_height}" '
        f'x2="{margin_left + chart_width}" y2="{margin_top + chart_height}" stroke="#cbd5e1"/>',
    ]

    for step in range(6):
        value = max_value * step / 5
        y = margin_top + chart_height - (value / max_value * chart_height)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{margin_left + chart_width}" '
            f'y2="{y:.1f}" stroke="#e2e8f0"/>'
        )
        parts.append(
            f'<text x="{margin_left - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-size="12" fill="#475569">{value:.2f}</text>'
        )

    for metric_index, metric in enumerate(metrics):
        group_x = margin_left + metric_index * group_width
        label_x = group_x + group_width / 2
        parts.append(
            f'<text x="{label_x:.1f}" y="{margin_top + chart_height + 28}" '
            f'text-anchor="middle" font-size="13" fill="#0f172a">{html.escape(metric)}</text>'
        )

        for row_index, row in enumerate(rows):
            value = to_float(row[metric])
            x = group_x + group_width / 2 - (len(rows) * bar_width) / 2 + row_index * bar_width
            bar_height = value / max_value * chart_height
            y = margin_top + chart_height - bar_height
            scenario = row["scenario"]
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width - 4:.1f}" '
                f'height="{bar_height:.1f}" fill="{scenario_color(scenario)}" rx="3"/>'
            )
            parts.append(
                f'<text x="{x + (bar_width - 4) / 2:.1f}" y="{y - 6:.1f}" '
                f'text-anchor="middle" font-size="11" fill="#334155">{value:.3f}</text>'
            )

    legend_x = margin_left
    legend_y = height - 34
    for index, row in enumerate(rows):
        x = legend_x + index * 190
        scenario = row["scenario"]
        parts.append(f'<rect x="{x}" y="{legend_y - 11}" width="14" height="14" fill="{scenario_color(scenario)}" rx="2"/>')
        parts.append(f'<text x="{x + 22}" y="{legend_y}" font-size="13" fill="#0f172a">{html.escape(scenario)}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def svg_histogram(rows_by_scenario, metric):
    width = 920
    height = 340
    margin_left = 58
    margin_top = 28
    chart_width = width - margin_left - 28
    chart_height = 230
    bins = [0.0, 0.001, 0.1, 0.2, 0.4, 0.6, 0.8, 1.01]
    labels = ["0", "<0.1", "<0.2", "<0.4", "<0.6", "<0.8", "1.0"]
    scenario_names = list(rows_by_scenario)
    counts_by_scenario = {}

    for scenario, rows in rows_by_scenario.items():
        counts = [0] * (len(bins) - 1)
        for row in rows:
            value = to_float(row[metric])
            for index in range(len(bins) - 1):
                if bins[index] <= value < bins[index + 1]:
                    counts[index] += 1
                    break
        counts_by_scenario[scenario] = counts

    max_count = max(max(counts) for counts in counts_by_scenario.values()) or 1
    group_width = chart_width / len(labels)
    bar_width = min(36, group_width / (len(scenario_names) + 1.4))

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(metric)} distribution">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<line x1="{margin_left}" y1="{margin_top + chart_height}" '
        f'x2="{margin_left + chart_width}" y2="{margin_top + chart_height}" stroke="#cbd5e1"/>',
    ]

    for step in range(5):
        count = max_count * step / 4
        y = margin_top + chart_height - (count / max_count * chart_height)
        parts.append(
            f'<line x1="{margin_left}" y1="{y:.1f}" x2="{margin_left + chart_width}" '
            f'y2="{y:.1f}" stroke="#e2e8f0"/>'
        )
        parts.append(
            f'<text x="{margin_left - 8}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-size="12" fill="#475569">{int(count)}</text>'
        )

    for bin_index, label in enumerate(labels):
        group_x = margin_left + bin_index * group_width
        parts.append(
            f'<text x="{group_x + group_width / 2:.1f}" y="{margin_top + chart_height + 28}" '
            f'text-anchor="middle" font-size="12" fill="#0f172a">{html.escape(label)}</text>'
        )

        for scenario_index, scenario in enumerate(scenario_names):
            count = counts_by_scenario[scenario][bin_index]
            x = group_x + group_width / 2 - (len(scenario_names) * bar_width) / 2 + scenario_index * bar_width
            bar_height = count / max_count * chart_height
            y = margin_top + chart_height - bar_height
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width - 4:.1f}" '
                f'height="{bar_height:.1f}" fill="{scenario_color(scenario)}" rx="3"/>'
            )

    parts.append(f'<text x="{margin_left}" y="{height - 22}" font-size="13" fill="#475569">Bins show per-query {html.escape(metric)} values.</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def svg_relevant_hits(rows_by_scenario):
    width = 920
    height = 320
    margin_left = 58
    margin_top = 28
    chart_width = width - margin_left - 28
    chart_height = 210
    scenario_names = list(rows_by_scenario)
    counters = {
        scenario: Counter(int(float(row["relevant_found@10"])) for row in rows)
        for scenario, rows in rows_by_scenario.items()
    }
    labels = list(range(0, 11))
    max_count = max(max(counter.values()) for counter in counters.values()) or 1
    group_width = chart_width / len(labels)
    bar_width = min(30, group_width / (len(scenario_names) + 1.3))

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Relevant hits at 10 distribution">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<line x1="{margin_left}" y1="{margin_top + chart_height}" '
        f'x2="{margin_left + chart_width}" y2="{margin_top + chart_height}" stroke="#cbd5e1"/>',
    ]

    for hits in labels:
        group_x = margin_left + hits * group_width
        parts.append(
            f'<text x="{group_x + group_width / 2:.1f}" y="{margin_top + chart_height + 26}" '
            f'text-anchor="middle" font-size="12" fill="#0f172a">{hits}</text>'
        )
        for scenario_index, scenario in enumerate(scenario_names):
            count = counters[scenario][hits]
            x = group_x + group_width / 2 - (len(scenario_names) * bar_width) / 2 + scenario_index * bar_width
            bar_height = count / max_count * chart_height
            y = margin_top + chart_height - bar_height
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width - 3:.1f}" '
                f'height="{bar_height:.1f}" fill="{scenario_color(scenario)}" rx="3"/>'
            )

    parts.append(f'<text x="{margin_left}" y="{height - 18}" font-size="13" fill="#475569">X axis: number of same-ISSN/same-venue hits in top 10.</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def summary_table(rows):
    headers = ["scenario", "bm25_weight", "dense_weight", "queries", *METRICS]
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = []
    for row in rows:
        cells = []
        for header in headers:
            value = row[header]
            if header in METRICS:
                value = f"{to_float(value):.4f}"
            cells.append(f"<td>{html.escape(str(value))}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def write_report(
    output_path,
    summary_rows,
    rows_by_scenario,
    report_title="no-MSC Hybrid Evaluation",
    description=(
        "Evaluation uses leave-one-out retrieval with same ISSN as relevance, "
        "falling back to same venue when ISSN is unavailable."
    ),
):
    charts = [
        ("Summary Metrics", svg_bar_chart(summary_rows, METRICS)),
        ("Relevant Hits @10", svg_relevant_hits(rows_by_scenario)),
        ("Precision @10 Distribution", svg_histogram(rows_by_scenario, "precision@10")),
        ("MRR @10 Distribution", svg_histogram(rows_by_scenario, "mrr@10")),
        ("nDCG @10 Distribution", svg_histogram(rows_by_scenario, "ndcg@10")),
    ]

    identical_note = ""
    if len(summary_rows) >= 2 and all(
        summary_rows[0].get(metric) == row.get(metric)
        for row in summary_rows[1:]
        for metric in METRICS
    ):
        identical_note = (
            "<p class=\"note\">The evaluated scenarios have identical aggregate "
            "metrics in this run. The charts intentionally show overlapping bars "
            "so that tie is visible.</p>"
        )

    chart_html = "\n".join(
        f"<section><h2>{html.escape(title)}</h2>{svg}</section>"
        for title, svg in charts
    )

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(report_title)}</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      color: #0f172a;
      background: #f8fafc;
    }}
    main {{
      max-width: 1060px;
      margin: 0 auto;
      padding: 28px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 18px;
    }}
    p {{
      color: #475569;
      line-height: 1.5;
    }}
    section {{
      margin-top: 22px;
      padding: 18px;
      background: white;
      border: 1px solid #dbe3ee;
      border-radius: 8px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: white;
      font-size: 14px;
    }}
    th, td {{
      padding: 9px 10px;
      border: 1px solid #dbe3ee;
      text-align: left;
    }}
    th {{
      background: #e2e8f0;
    }}
    .note {{
      padding: 10px 12px;
      background: #fff7ed;
      border: 1px solid #fed7aa;
      color: #9a3412;
      border-radius: 6px;
    }}
  </style>
</head>
<body>
<main>
  <h1>{html.escape(report_title)}</h1>
  <p>{html.escape(description)}</p>
  {identical_note}
  <section>
    <h2>Metric Table</h2>
    {summary_table(summary_rows)}
  </section>
  {chart_html}
</main>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Create HTML/SVG visualizations for no-MSC hybrid evaluation results."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=BASE_DIR / "output" / "opensearch_evaluation",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE_DIR / "output" / "opensearch_evaluation" / "hybrid_evaluation_report.html",
    )
    parser.add_argument("--title", default="no-MSC Hybrid Evaluation")
    parser.add_argument(
        "--description",
        default=(
            "Evaluation uses leave-one-out retrieval with same ISSN as relevance, "
            "falling back to same venue when ISSN is unavailable."
        ),
    )
    args = parser.parse_args()

    summary_rows = read_csv(args.input_dir / "summary.csv")
    rows_by_scenario = {
        row["scenario"]: read_csv(args.input_dir / f"{row['scenario']}_details.csv")
        for row in summary_rows
    }

    write_report(args.output, summary_rows, rows_by_scenario, args.title, args.description)
    print("[DONE] hybrid evaluation visualizations")
    print(f"  report : {args.output}")


if __name__ == "__main__":
    main()
