#!/usr/bin/env python3
"""Main experiment campaign for policy-aware contract testing.

This script is intentionally mechanism-driven rather than seed-driven. It runs
the benchmark once, then derives experiment tables that explain which contract
dimension is responsible for each detection or miss.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import defaultdict
from pathlib import Path

import policy_contract_benchmark as bench


PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PROJECT / "results" / "main_experiment"
CORE_BASELINES = (
    "schema_validation",
    "auth_required",
    "role_matrix",
    "object_policy_tests",
    "field_policy_tests",
    "audit_contract_tests",
    "deprecated_inventory_tests",
)
ABLATIONS = (
    "full_without_object_scope",
    "full_without_field_scope",
    "full_without_audit",
    "full_without_purpose",
)
PROPOSED = "policy_aware_full"


def run_campaign(seed: int, multiplier: int = 1) -> dict:
    rng = random.Random(seed)
    policies = bench.replicated_policies(bench.domains(), multiplier)
    variants = bench.make_variants(policies)
    policy_map = {bench.policy_id(policy): policy for policy in policies}
    tests_by_policy = {bench.policy_id(policy): bench.make_tests(policy, rng) for policy in policies}
    all_tests = [test for tests in tests_by_policy.values() for test in tests]

    findings = []
    for variant in variants:
        policy = policy_map[variant.policy_id]
        tests = tests_by_policy[variant.policy_id]
        execution_trace = bench.materialize_execution(policy, variant, tests)
        for method in bench.METHODS:
            findings.extend(bench.run_method(method, policy, variant.variant_id, tests, execution_trace))

    detections, summary, by_family = bench.summarize_detection(findings, variants)
    miss_rows = bench.fault_dimension_miss_analysis(detections, findings, variants)
    miss_summary = bench.fault_dimension_miss_summary(miss_rows)

    return {
        "seed": seed,
        "multiplier": multiplier,
        "policies": policies,
        "policy_map": policy_map,
        "variants": variants,
        "tests_by_policy": tests_by_policy,
        "all_tests": all_tests,
        "findings": findings,
        "detections": detections,
        "summary": summary,
        "by_family": by_family,
        "miss_rows": miss_rows,
        "miss_summary": miss_summary,
    }


def first_detection_triggers(campaign: dict) -> list[dict]:
    by_method_variant = defaultdict(list)
    for finding in campaign["findings"]:
        if finding.detected:
            by_method_variant[(finding.method, finding.variant_id)].append(finding)

    rows = []
    variant_by_id = {variant.variant_id: variant for variant in campaign["variants"]}
    for (method, variant_id), findings in sorted(by_method_variant.items()):
        variant = variant_by_id[variant_id]
        if variant.bug_type == "correct":
            continue
        ranked = sorted(findings, key=lambda item: item.test_id)
        first = ranked[0]
        rows.append({
            "method": method,
            "variant_id": variant_id,
            "domain": variant.domain,
            "endpoint": variant.endpoint,
            "bug_type": variant.bug_type,
            "family": variant.family,
            "primary_dimension": bench.PRIMARY_DIMENSION_BY_BUG.get(variant.bug_type, "unknown"),
            "first_trigger_test": first.test_id.split("::test_", 1)[1].split("_", 1)[1],
            "trigger_reason": first.reason,
            "n_triggering_tests": len(ranked),
            "risk": round(variant.risk, 4),
        })
    return rows


def exposure_events(campaign: dict) -> list[dict]:
    rows = []
    for variant in campaign["variants"]:
        if variant.bug_type == "correct":
            continue
        policy = campaign["policy_map"][variant.policy_id]
        for test in campaign["tests_by_policy"][variant.policy_id]:
            response = bench.apply_variant(policy, variant.bug_type, test)
            violation, reasons, risk = bench.expected_violation(policy, test, response)
            if not violation:
                continue
            expected_allow = bench.policy_allows(policy, test.actor, test.obj)
            expected_fields = set(bench.allowed_fields(policy, test.actor)) & set(test.requested_fields) if expected_allow else set()
            observed_fields = set(response.fields)
            extra_fields = sorted(observed_fields - expected_fields)
            sensitivities = [
                field.sensitivity
                for field in policy.fields
                if field.name in extra_fields
            ]
            rows.append({
                "variant_id": variant.variant_id,
                "domain": variant.domain,
                "endpoint": variant.endpoint,
                "bug_type": variant.bug_type,
                "family": variant.family,
                "primary_dimension": bench.PRIMARY_DIMENSION_BY_BUG.get(variant.bug_type, "unknown"),
                "test_kind": test.test_kind,
                "reasons": ";".join(reasons),
                "allowed": int(response.allowed),
                "extra_field_count": len(extra_fields),
                "extra_sensitive_field_count": sum(
                    1 for sensitivity in sensitivities if bench.SENSITIVITY_WEIGHT[sensitivity] >= 3
                ),
                "max_extra_sensitivity": max(
                    [bench.SENSITIVITY_WEIGHT[sensitivity] for sensitivity in sensitivities],
                    default=0,
                ),
                "risk": round(risk, 4),
            })
    return rows


def exposure_summary(events: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for event in events:
        grouped[(event["bug_type"], event["primary_dimension"])].append(event)
    rows = []
    for (bug_type, dimension), items in sorted(grouped.items()):
        rows.append({
            "bug_type": bug_type,
            "primary_dimension": dimension,
            "violation_events": len(items),
            "events_with_extra_fields": sum(1 for item in items if item["extra_field_count"] > 0),
            "total_extra_fields": sum(item["extra_field_count"] for item in items),
            "total_extra_sensitive_fields": sum(item["extra_sensitive_field_count"] for item in items),
            "max_extra_sensitivity": max(item["max_extra_sensitivity"] for item in items),
            "total_event_risk": round(sum(float(item["risk"]) for item in items), 4),
        })
    return rows


def baseline_failure_mechanisms(campaign: dict) -> list[dict]:
    detections_by_key = {
        (row["method"], row["variant_id"]): row
        for row in campaign["detections"]
        if row["ground_truth_bug"]
    }
    variant_by_id = {variant.variant_id: variant for variant in campaign["variants"]}
    rows = []
    for method in CORE_BASELINES:
        for variant in campaign["variants"]:
            if variant.bug_type == "correct":
                continue
            detected = detections_by_key[(method, variant.variant_id)]["detected"]
            rows.append({
                "method": method,
                "bug_type": variant.bug_type,
                "family": variant.family,
                "primary_dimension": bench.PRIMARY_DIMENSION_BY_BUG.get(variant.bug_type, "unknown"),
                "detected": int(detected),
                "missed": int(not detected),
                "risk": round(variant.risk, 4),
            })
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["method"], row["bug_type"], row["family"], row["primary_dimension"])].append(row)
    out = []
    for (method, bug_type, family, dimension), items in sorted(grouped.items()):
        total = len(items)
        detected = sum(item["detected"] for item in items)
        risk_total = sum(float(item["risk"]) for item in items)
        risk_detected = sum(float(item["risk"]) for item in items if item["detected"])
        out.append({
            "method": method,
            "bug_type": bug_type,
            "family": family,
            "primary_dimension": dimension,
            "n": total,
            "detected": detected,
            "missed": total - detected,
            "recall": round(detected / total, 4),
            "risk_weighted_recall": round(risk_detected / risk_total, 4) if risk_total else 0.0,
            "risk_missed": round(risk_total - risk_detected, 4),
        })
    return out


def ablation_loss(campaign: dict) -> list[dict]:
    detections = {
        (row["method"], row["variant_id"]): row
        for row in campaign["detections"]
        if row["ground_truth_bug"]
    }
    rows = []
    for variant in campaign["variants"]:
        if variant.bug_type == "correct":
            continue
        proposed = detections[(PROPOSED, variant.variant_id)]
        for method in ABLATIONS:
            ablated = detections[(method, variant.variant_id)]
            rows.append({
                "ablation": method,
                "variant_id": variant.variant_id,
                "bug_type": variant.bug_type,
                "family": variant.family,
                "primary_dimension": bench.PRIMARY_DIMENSION_BY_BUG.get(variant.bug_type, "unknown"),
                "lost_detection": int(proposed["detected"] and not ablated["detected"]),
                "risk_lost": round(float(proposed["risk"]) if proposed["detected"] and not ablated["detected"] else 0.0, 4),
            })
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["ablation"], row["primary_dimension"], row["bug_type"])].append(row)
    out = []
    for (ablation, dimension, bug_type), items in sorted(grouped.items()):
        out.append({
            "ablation": ablation,
            "primary_dimension": dimension,
            "bug_type": bug_type,
            "n": len(items),
            "lost_detections": sum(item["lost_detection"] for item in items),
            "risk_lost": round(sum(float(item["risk_lost"]) for item in items), 4),
        })
    return out


def casebook(campaign: dict) -> list[dict]:
    rows = []
    seen = set()
    for row in campaign["miss_rows"]:
        key = (row["method"], row["primary_missing_dimension"])
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "method": row["method"],
            "primary_missing_dimension": row["primary_missing_dimension"],
            "root_cause": row["root_cause"],
            "example_domain": row["domain"],
            "example_endpoint": row["endpoint"],
            "example_bug_type": row["bug_type"],
            "oracle_reasons": row["oracle_reasons"],
            "evidence_test_kinds": row["evidence_test_kinds"],
            "interpretation": interpretation_for(row["method"], row["primary_missing_dimension"]),
        })
    return rows


def interpretation_for(method: str, dimension: str) -> str:
    if method == "schema_validation":
        return "The response can remain structurally valid while violating a policy obligation."
    if dimension in {"object_scope", "jurisdiction_scope"}:
        return "The baseline lacks a subject-resource predicate and cannot distinguish same-role cross-object access."
    if dimension == "field_minimization":
        return "The baseline checks allow or deny decisions but not whether the response is minimized to allowed fields."
    if dimension == "aggregation_boundary":
        return "The baseline has no aggregate/export boundary oracle, so detailed records can leak through bulk responses."
    if dimension == "purpose_scope":
        return "The baseline treats role membership as sufficient and does not test purpose-bound access."
    if dimension == "audit_obligation":
        return "The baseline observes the API decision but not the required audit side effect."
    if dimension == "endpoint_inventory":
        return "The baseline does not test whether deprecated endpoints remain reachable."
    if dimension == "authentication":
        return "The baseline does not exercise unauthenticated access for this policy obligation."
    if dimension == "function_authorization":
        return "The baseline does not exercise a disallowed role at the function boundary."
    return "The baseline lacks the oracle required for this policy obligation."


def main_report(campaign: dict, tables: dict[str, list[dict]], elapsed: float) -> str:
    best = max(campaign["summary"], key=lambda row: (row["risk_weighted_recall"], row["recall"]))
    lines = [
        "# Main Experiment Report",
        "",
        "## Campaign",
        "",
        f"- Policies/endpoints: {len(campaign['policies'])}",
        f"- Variants: {len(campaign['variants'])}",
        f"- Injected buggy variants: {sum(1 for variant in campaign['variants'] if variant.bug_type != 'correct')}",
        f"- Test cases: {len(campaign['all_tests'])}",
        f"- Test-level findings: {len(campaign['findings'])}",
        f"- Elapsed seconds: {round(elapsed, 4)}",
        "",
        "## Primary Result",
        "",
        f"- Best method: `{best['method']}`",
        f"- Recall: {best['recall']}",
        f"- F1: {best['f1']}",
        f"- Risk-weighted recall: {best['risk_weighted_recall']}",
        "",
        "## Method Summary",
        "",
        "| Method | Precision | Recall | F1 | Risk-weighted recall |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in sorted(campaign["summary"], key=lambda item: item["risk_weighted_recall"], reverse=True):
        lines.append(f"| {row['method']} | {row['precision']} | {row['recall']} | {row['f1']} | {row['risk_weighted_recall']} |")

    lines.extend([
        "",
        "## Largest Baseline Miss Mechanisms",
        "",
        "| Method | Bug type | Primary dimension | Recall | Risk missed |",
        "|---|---|---|---:|---:|",
    ])
    for row in sorted(tables["baseline_failure_mechanisms"], key=lambda item: item["risk_missed"], reverse=True)[:18]:
        lines.append(f"| {row['method']} | {row['bug_type']} | {row['primary_dimension']} | {row['recall']} | {row['risk_missed']} |")

    lines.extend([
        "",
        "## Exposure Summary",
        "",
        "| Bug type | Dimension | Events | Extra fields | Sensitive extra fields | Event risk |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for row in sorted(tables["exposure_summary"], key=lambda item: item["total_event_risk"], reverse=True):
        lines.append(
            f"| {row['bug_type']} | {row['primary_dimension']} | {row['violation_events']} | "
            f"{row['total_extra_fields']} | {row['total_extra_sensitive_fields']} | {row['total_event_risk']} |"
        )

    lines.extend([
        "",
        "## Ablation Loss",
        "",
        "| Ablation | Dimension | Bug type | Lost detections | Risk lost |",
        "|---|---|---|---:|---:|",
    ])
    for row in sorted(tables["ablation_loss"], key=lambda item: item["risk_lost"], reverse=True)[:18]:
        if row["lost_detections"]:
            lines.append(
                f"| {row['ablation']} | {row['primary_dimension']} | {row['bug_type']} | "
                f"{row['lost_detections']} | {row['risk_lost']} |"
            )

    lines.extend([
        "",
        "## Main Interpretation",
        "",
        "- Schema validation remains blind to policy bugs when responses are structurally valid.",
        "- Role matrices detect coarse function authorization but miss object, jurisdiction, purpose, field, audit, and inventory obligations.",
        "- Object-policy and field-policy tests each detect their own family but leave large missed-risk regions.",
        "- The proposed suite is strongest because it combines decision, response-minimization, side-effect, and inventory oracles.",
    ])
    return "\n".join(lines) + "\n"


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260616)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--multiplier", type=int, default=1)
    args = parser.parse_args()

    started = time.perf_counter()
    out_dir = Path(args.out_dir)
    campaign = run_campaign(args.seed, args.multiplier)

    tables = {
        "first_detection_triggers": first_detection_triggers(campaign),
        "exposure_events": exposure_events(campaign),
        "baseline_failure_mechanisms": baseline_failure_mechanisms(campaign),
        "ablation_loss": ablation_loss(campaign),
        "casebook": casebook(campaign),
    }
    tables["exposure_summary"] = exposure_summary(tables["exposure_events"])
    elapsed = time.perf_counter() - started

    out_dir.mkdir(parents=True, exist_ok=True)
    bench.write_csv(out_dir / "method_summary.csv", campaign["summary"])
    bench.write_csv(out_dir / "recall_by_bug_family.csv", campaign["by_family"])
    bench.write_csv(out_dir / "fault_dimension_miss_analysis.csv", campaign["miss_rows"])
    bench.write_csv(out_dir / "fault_dimension_miss_summary.csv", campaign["miss_summary"])
    for name, rows in tables.items():
        bench.write_csv(out_dir / f"{name}.csv", rows)
    (out_dir / "MAIN_EXPERIMENT_REPORT.md").write_text(
        main_report(campaign, tables, elapsed),
        encoding="utf-8",
    )
    write_json(out_dir / "main_experiment_summary.json", {
        "seed": args.seed,
        "multiplier": args.multiplier,
        "elapsed_seconds": round(elapsed, 4),
        "policies": len(campaign["policies"]),
        "variants": len(campaign["variants"]),
        "buggy_variants": sum(1 for variant in campaign["variants"] if variant.bug_type != "correct"),
        "test_cases": len(campaign["all_tests"]),
        "findings": len(campaign["findings"]),
        "tables": {name: len(rows) for name, rows in tables.items()},
    })
    print(f"wrote main experiment results to {out_dir}")


if __name__ == "__main__":
    main()
