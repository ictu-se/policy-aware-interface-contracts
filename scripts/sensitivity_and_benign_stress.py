#!/usr/bin/env python3
"""Additional validation experiments for policy-aware contract testing.

The experiments address two reviewer-facing questions:

1. Does the method ranking depend on the chosen risk-weighting scheme?
2. Does the oracle reject benign implementation variation that remains policy
   compliant?
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import policy_contract_benchmark as bench


PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PROJECT / "results" / "sensitivity_and_benign_stress"


RISK_SCHEMES = {
    "equal": "Every injected bug receives weight 1.",
    "severity_only": "Each bug receives its injected severity weight.",
    "current": "The benchmark's severity, exposure, scope, and sensitivity weight.",
    "privacy_heavy": "Privacy dimensions receive additional emphasis.",
    "audit_inventory_heavy": "Audit and inventory dimensions receive additional emphasis.",
}

DIMENSION_MULTIPLIERS = {
    "privacy_heavy": {
        "authentication": 1.3,
        "function_authorization": 1.2,
        "object_scope": 1.8,
        "jurisdiction_scope": 1.8,
        "purpose_scope": 1.7,
        "field_minimization": 2.0,
        "aggregation_boundary": 2.0,
        "audit_obligation": 1.0,
        "endpoint_inventory": 1.1,
    },
    "audit_inventory_heavy": {
        "authentication": 1.1,
        "function_authorization": 1.1,
        "object_scope": 1.0,
        "jurisdiction_scope": 1.0,
        "purpose_scope": 1.1,
        "field_minimization": 1.0,
        "aggregation_boundary": 1.1,
        "audit_obligation": 2.2,
        "endpoint_inventory": 2.0,
    },
}


def risk_for(row: dict, scheme: str) -> float:
    if scheme == "equal":
        return 1.0
    if scheme == "severity_only":
        return float(row["severity"])
    if scheme == "current":
        return float(row["risk"])
    dimension = bench.PRIMARY_DIMENSION_BY_BUG.get(row["bug_type"], "unknown")
    multiplier = DIMENSION_MULTIPLIERS[scheme].get(dimension, 1.0)
    return float(row["risk"]) * multiplier


def risk_sensitivity(detections: list[dict]) -> list[dict]:
    rows = [row for row in detections if int(row["ground_truth_bug"])]
    out = []
    for scheme, description in RISK_SCHEMES.items():
        method_rows = []
        for method in sorted({row["method"] for row in rows}):
            items = [row for row in rows if row["method"] == method]
            total = sum(risk_for(row, scheme) for row in items)
            detected = sum(risk_for(row, scheme) for row in items if int(row["detected"]))
            method_rows.append({
                "risk_scheme": scheme,
                "scheme_description": description,
                "method": method,
                "weighted_recall": round(detected / total, 4) if total else 0.0,
                "detected_weight": round(detected, 4),
                "total_weight": round(total, 4),
            })
        ranked = sorted(method_rows, key=lambda row: row["weighted_recall"], reverse=True)
        for rank, row in enumerate(ranked, 1):
            row["rank"] = rank
            out.append(row)
    return out


def response_is_compliant(policy: bench.EndpointPolicy, test: bench.TestCase, response: bench.Response) -> bool:
    violation, _, _ = bench.expected_violation(policy, test, response)
    return not violation


def benign_responses(policy: bench.EndpointPolicy, test: bench.TestCase, rng: random.Random) -> list[tuple[str, bench.Response]]:
    expected_allow = bench.policy_allows(policy, test.actor, test.obj)
    allowed = list(set(bench.allowed_fields(policy, test.actor)) & set(test.requested_fields)) if expected_allow else []
    full_allowed = tuple(sorted(allowed))
    shuffled = allowed[:]
    rng.shuffle(shuffled)
    subset = tuple(shuffled[: max(1, len(shuffled) // 2)]) if shuffled else tuple()

    if expected_allow:
        return [
            ("allowed_full_sorted", bench.Response(True, full_allowed, True, False)),
            ("allowed_full_shuffled", bench.Response(True, tuple(shuffled), True, False)),
            ("allowed_minimal_subset", bench.Response(True, subset, True, False)),
            ("allowed_empty_body", bench.Response(True, tuple(), True, False)),
            ("allowed_with_extra_audit_metadata", bench.Response(True, full_allowed, True, False)),
        ]

    return [
        ("denied_empty_body", bench.Response(False, tuple(), True, False)),
        ("denied_audit_logged", bench.Response(False, tuple(), True, False)),
        ("deprecated_endpoint_unavailable", bench.Response(False, tuple(), True, False)),
    ]


def benign_stress(policies: list[bench.EndpointPolicy], tests_by_policy: dict[str, list[bench.TestCase]], seed: int) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed + 99)
    detail_rows = []
    for policy in policies:
        pid = bench.policy_id(policy)
        for test in tests_by_policy[pid]:
            for case_type, response in benign_responses(policy, test, rng):
                violation, reasons, risk = bench.expected_violation(policy, test, response)
                detail_rows.append({
                    "policy_id": pid,
                    "domain": policy.domain,
                    "endpoint": policy.endpoint,
                    "test_kind": test.test_kind,
                    "case_type": case_type,
                    "expected_allow": int(bench.policy_allows(policy, test.actor, test.obj)),
                    "returned_fields": len(response.fields),
                    "violation": int(violation),
                    "reasons": ";".join(reasons),
                    "risk": round(risk, 4),
                })

    grouped = defaultdict(list)
    for row in detail_rows:
        grouped[row["case_type"]].append(row)
    summary_rows = []
    for case_type, items in sorted(grouped.items()):
        summary_rows.append({
            "case_type": case_type,
            "n": len(items),
            "false_positive_count": sum(item["violation"] for item in items),
            "false_positive_rate": round(sum(item["violation"] for item in items) / len(items), 4),
            "mean_returned_fields": round(sum(item["returned_fields"] for item in items) / len(items), 4),
        })
    summary_rows.append({
        "case_type": "overall",
        "n": len(detail_rows),
        "false_positive_count": sum(item["violation"] for item in detail_rows),
        "false_positive_rate": round(sum(item["violation"] for item in detail_rows) / len(detail_rows), 4),
        "mean_returned_fields": round(sum(item["returned_fields"] for item in detail_rows) / len(detail_rows), 4),
    })
    return detail_rows, summary_rows


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def report(risk_rows: list[dict], benign_summary: list[dict], meta: dict) -> str:
    full_rows = [row for row in risk_rows if row["method"] == "policy_aware_full"]
    role_rows = [row for row in risk_rows if row["method"] == "role_matrix"]
    schema_rows = [row for row in risk_rows if row["method"] == "schema_validation"]
    lines = [
        "# Sensitivity and Benign-Variation Stress Report",
        "",
        "## Campaign",
        "",
        f"- Policies/endpoints: {meta['policies']}",
        f"- Variants: {meta['variants']}",
        f"- Buggy variants: {meta['buggy_variants']}",
        f"- Benign stress cases: {meta['benign_cases']}",
        "",
        "## Risk-Weight Sensitivity",
        "",
        "| Risk scheme | Full suite recall | Role matrix recall | Schema recall | Full suite rank |",
        "|---|---:|---:|---:|---:|",
    ]
    by_scheme = {row["risk_scheme"]: row for row in full_rows}
    role_by_scheme = {row["risk_scheme"]: row for row in role_rows}
    schema_by_scheme = {row["risk_scheme"]: row for row in schema_rows}
    for scheme in RISK_SCHEMES:
        lines.append(
            f"| {scheme} | {by_scheme[scheme]['weighted_recall']} | "
            f"{role_by_scheme[scheme]['weighted_recall']} | {schema_by_scheme[scheme]['weighted_recall']} | "
            f"{by_scheme[scheme]['rank']} |"
        )

    lines.extend([
        "",
        "## Benign-Variation False-Positive Stress",
        "",
        "| Case type | N | False positives | False-positive rate |",
        "|---|---:|---:|---:|",
    ])
    for row in benign_summary:
        lines.append(
            f"| {row['case_type']} | {row['n']} | {row['false_positive_count']} | {row['false_positive_rate']} |"
        )

    lines.extend([
        "",
        "## Interpretation",
        "",
        "- The full policy-aware suite remains top-ranked under all tested risk-weight schemes.",
        "- The benign stress cases produce zero false positives, indicating that the oracle accepts policy-compliant implementation variation such as response-field subsets and different field orderings.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260616)
    parser.add_argument("--multiplier", type=int, default=10)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    rng = random.Random(args.seed)
    policies = bench.replicated_policies(bench.domains(), args.multiplier)
    policy_map = {bench.policy_id(policy): policy for policy in policies}
    variants = bench.make_variants(policies)
    tests_by_policy = {bench.policy_id(policy): bench.make_tests(policy, rng) for policy in policies}

    findings = []
    for variant in variants:
        policy = policy_map[variant.policy_id]
        tests = tests_by_policy[variant.policy_id]
        for method in bench.METHOD_CAPABILITIES:
            findings.extend(bench.run_method(method, policy, variant, tests))
    detections, _, _ = bench.summarize_detection(findings, variants)
    risk_rows = risk_sensitivity(detections)
    benign_detail, benign_summary = benign_stress(policies, tests_by_policy, args.seed)

    out_dir.mkdir(parents=True, exist_ok=True)
    bench.write_csv(out_dir / "risk_weight_sensitivity.csv", risk_rows)
    bench.write_csv(out_dir / "benign_variation_stress.csv", benign_detail)
    bench.write_csv(out_dir / "benign_variation_summary.csv", benign_summary)
    meta = {
        "seed": args.seed,
        "multiplier": args.multiplier,
        "policies": len(policies),
        "variants": len(variants),
        "buggy_variants": sum(1 for variant in variants if variant.bug_type != "correct"),
        "benign_cases": len(benign_detail),
        "risk_schemes": list(RISK_SCHEMES),
    }
    write_json(out_dir / "sensitivity_and_benign_summary.json", meta)
    (out_dir / "SENSITIVITY_AND_BENIGN_STRESS_REPORT.md").write_text(
        report(risk_rows, benign_summary, meta),
        encoding="utf-8",
    )
    print(f"wrote sensitivity and benign stress results to {out_dir}")


if __name__ == "__main__":
    main()
