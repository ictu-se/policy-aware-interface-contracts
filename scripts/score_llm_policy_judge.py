#!/usr/bin/env python3
"""Score local LLM policy-judge outputs against deterministic oracle labels."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT / "results" / "llm_policy_judge"


def load_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = list(rows[0].keys())
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def score_file(path: Path, allowed_case_ids: set[str] | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    rows = list(load_jsonl(path))
    if allowed_case_ids is not None:
        rows = [row for row in rows if row.get("case_id") in allowed_case_ids]
    if not rows:
        return [], [], []
    model = rows[0]["model"]
    scored = []
    for row in rows:
        oracle = int(row["oracle_violation"])
        pred = int(row.get("predicted_violation", 0))
        oracle_dim = row.get("oracle_primary_dimension", "none")
        pred_dim = row.get("predicted_primary_dimension", "")
        scored.append({
            "model": model,
            "case_id": row["case_id"],
            "domain": row["domain"],
            "endpoint": row["endpoint"],
            "bug_type": row["bug_type"],
            "family": row["family"],
            "test_kind": row["test_kind"],
            "oracle_violation": oracle,
            "predicted_violation": pred,
            "oracle_primary_dimension": oracle_dim,
            "predicted_primary_dimension": pred_dim,
            "parse_ok": int(row.get("parse_ok", 0)),
            "decision_correct": int(oracle == pred),
            "dimension_correct": int(oracle_dim == pred_dim),
            "strict_correct": int(oracle == pred and (oracle == 0 or oracle_dim == pred_dim)),
            "elapsed_sec": row.get("elapsed_sec", ""),
            "oracle_risk": row.get("oracle_risk", 0.0),
        })

    summary = summarize(scored, "overall", "all")
    by_dimension = []
    for dimension in sorted({row["oracle_primary_dimension"] for row in scored}):
        by_dimension.append(summarize([row for row in scored if row["oracle_primary_dimension"] == dimension], "dimension", dimension))
    by_family = []
    for family in sorted({row["family"] for row in scored}):
        by_family.append(summarize([row for row in scored if row["family"] == family], "family", family))
    return scored, [summary], by_dimension + by_family


def summarize(rows: list[dict], group_type: str, group_value: str) -> dict:
    n = len(rows)
    tp = sum(1 for row in rows if row["oracle_violation"] and row["predicted_violation"])
    tn = sum(1 for row in rows if not row["oracle_violation"] and not row["predicted_violation"])
    fp = sum(1 for row in rows if not row["oracle_violation"] and row["predicted_violation"])
    fn = sum(1 for row in rows if row["oracle_violation"] and not row["predicted_violation"])
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    risk_total = sum(float(row["oracle_risk"]) for row in rows if row["oracle_violation"])
    risk_detected = sum(float(row["oracle_risk"]) for row in rows if row["oracle_violation"] and row["predicted_violation"])
    return {
        "model": rows[0]["model"] if rows else "",
        "group_type": group_type,
        "group_value": group_value,
        "n": n,
        "parse_rate": round(sum(row["parse_ok"] for row in rows) / n, 4) if n else 0.0,
        "decision_accuracy": round(sum(row["decision_correct"] for row in rows) / n, 4) if n else 0.0,
        "strict_accuracy": round(sum(row["strict_correct"] for row in rows) / n, 4) if n else 0.0,
        "dimension_accuracy_on_violations": round(
            sum(row["dimension_correct"] for row in rows if row["oracle_violation"]) / max(1, sum(row["oracle_violation"] for row in rows)),
            4,
        ),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "risk_weighted_recall": round(risk_detected / risk_total, 4) if risk_total else 0.0,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def write_report(path: Path, summary_rows: list[dict], group_rows: list[dict], common_case_count: int | None = None) -> None:
    lines = [
        "# LLM Policy-Judge Summary",
        "",
        "## Overall",
        "",
        "| Model | N | Parse | Decision acc. | Strict acc. | Precision | Recall | F1 | Risk recall |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(summary_rows, key=lambda item: item["strict_accuracy"], reverse=True):
        lines.append(
            f"| {row['model']} | {row['n']} | {row['parse_rate']} | {row['decision_accuracy']} | "
            f"{row['strict_accuracy']} | {row['precision']} | {row['recall']} | {row['f1']} | {row['risk_weighted_recall']} |"
        )
    if common_case_count is not None:
        lines.extend([
            "",
            f"Main comparison uses the {common_case_count} case IDs present for every scored model.",
        ])
    lines.extend([
        "",
        "## Lowest Dimension Groups",
        "",
        "| Model | Group | N | Strict acc. | Dimension acc. | Recall |",
        "|---|---|---:|---:|---:|---:|",
    ])
    focus = [row for row in group_rows if row["group_type"] == "dimension" and row["group_value"] != "none"]
    for row in sorted(focus, key=lambda item: (item["strict_accuracy"], item["model"]))[:30]:
        lines.append(
            f"| {row['model']} | {row['group_value']} | {row['n']} | {row['strict_accuracy']} | "
            f"{row['dimension_accuracy_on_violations']} | {row['recall']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default=str(RESULTS))
    parser.add_argument(
        "--all-cases",
        action="store_true",
        help="Score every row in every model file instead of restricting to case IDs shared by all models.",
    )
    args = parser.parse_args()
    results_dir = Path(args.results_dir)
    files = sorted(results_dir.glob("*_policy_judge_outputs.jsonl"))
    common_case_ids = None
    if files and not args.all_cases:
        case_sets = []
        for path in files:
            case_sets.append({row["case_id"] for row in load_jsonl(path)})
        common_case_ids = set.intersection(*case_sets) if case_sets else set()
    all_scored = []
    all_summary = []
    all_groups = []
    for path in files:
        scored, summary, groups = score_file(path, common_case_ids)
        all_scored.extend(scored)
        all_summary.extend(summary)
        all_groups.extend(groups)
    write_csv(results_dir / "llm_policy_judge_scored.csv", all_scored)
    write_csv(results_dir / "llm_policy_judge_summary.csv", all_summary)
    write_csv(results_dir / "llm_policy_judge_by_group.csv", all_groups)
    write_report(results_dir / "LLM_POLICY_JUDGE_SUMMARY.md", all_summary, all_groups, len(common_case_ids) if common_case_ids is not None else None)
    mode = f"common {len(common_case_ids)} cases" if common_case_ids is not None else "all cases"
    print(f"scored {len(files)} files in {results_dir} ({mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
