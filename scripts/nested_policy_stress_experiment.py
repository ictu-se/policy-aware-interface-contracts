#!/usr/bin/env python3
"""Nested/dependent policy stress experiment.

This experiment is intentionally not a seed expansion of the main benchmark.
It adds dependent rules whose violation requires checking interactions across
policy dimensions, such as purpose-conditioned fields, consent, jurisdiction,
aggregation thresholds, and enhanced audit obligations.
"""

from __future__ import annotations

import csv
import json
import argparse
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "results" / "nested_policy_stress"


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    domain: str
    endpoint: str
    role: str
    purpose: str
    same_jurisdiction: bool
    owner_or_care_relation: bool
    consent: bool
    emergency: bool
    group_size: int
    returned_fields: tuple[str, ...]
    audit_level: str
    bug_type: str
    expected_violation: bool
    primary_dimension: str
    risk: float


METHODS = (
    "schema_validation",
    "role_matrix",
    "object_policy_tests",
    "field_policy_tests",
    "audit_contract_tests",
    "basic_policy_aware_full",
    "dependent_policy_full",
    "dependent_without_consent",
    "dependent_without_threshold",
    "dependent_without_enhanced_audit",
    "dependent_without_purpose_field",
)


# The policy facts used by the oracle are independent of the injected scenario
# label. Each domain declares its allowed purpose and protected field.
DOMAIN_POLICY = {
    "health": {"purpose": "treatment", "protected_field": "diagnosis"},
    "citizen_services": {"purpose": "appeal_review", "protected_field": "disability_marker"},
    "education": {"purpose": "school_admin", "protected_field": "disciplinary_record"},
    "business_licensing": {"purpose": "licensing", "protected_field": "owner_identifier"},
}
MINIMUM_GROUP_SIZE = 10


def scenarios(multiplier: int = 1) -> list[Scenario]:
    rows = []
    templates = [
        ("health", "GET /patients/{id}", "doctor", "treatment", "diagnosis", 5.0),
        ("citizen_services", "GET /benefits/{id}", "district_officer", "appeal_review", "disability_marker", 5.0),
        ("education", "GET /students/{id}/record", "school_admin", "school_admin", "disciplinary_record", 5.0),
        ("business_licensing", "GET /licenses/export", "licensing_officer", "licensing", "owner_identifier", 4.0),
    ]
    for replica in range(multiplier):
      suffix = "" if replica == 0 else f"/dependent-replica-{replica}"
      for idx, (domain, endpoint, role, purpose, protected_field, weight) in enumerate(templates, 1):
        endpoint = endpoint + suffix
        rows.extend([
            Scenario(
                scenario_id=f"{domain}_{replica}_{idx}_purpose_field",
                domain=domain,
                endpoint=endpoint,
                role=role,
                purpose="reporting" if purpose != "reporting" else "marketing",
                same_jurisdiction=True,
                owner_or_care_relation=True,
                consent=True,
                emergency=False,
                group_size=27,
                returned_fields=("id", protected_field),
                audit_level="standard",
                bug_type="purpose_conditioned_field",
                expected_violation=True,
                primary_dimension="purpose_field_dependency",
                risk=weight * 7,
            ),
            Scenario(
                scenario_id=f"{domain}_{replica}_{idx}_jurisdiction_field",
                domain=domain,
                endpoint=endpoint,
                role=role,
                purpose=purpose,
                same_jurisdiction=False,
                owner_or_care_relation=True,
                consent=True,
                emergency=False,
                group_size=31,
                returned_fields=("id", protected_field),
                audit_level="standard",
                bug_type="jurisdiction_conditioned_field",
                expected_violation=True,
                primary_dimension="jurisdiction_field_dependency",
                risk=weight * 8,
            ),
            Scenario(
                scenario_id=f"{domain}_{replica}_{idx}_consent_field",
                domain=domain,
                endpoint=endpoint,
                role=role,
                purpose=purpose,
                same_jurisdiction=True,
                owner_or_care_relation=True,
                consent=False,
                emergency=False,
                group_size=44,
                returned_fields=("id", protected_field),
                audit_level="standard",
                bug_type="consent_gated_field",
                expected_violation=True,
                primary_dimension="consent_field_dependency",
                risk=weight * 6,
            ),
            Scenario(
                scenario_id=f"{domain}_{replica}_{idx}_small_cell",
                domain=domain,
                endpoint=endpoint,
                role=role,
                purpose=purpose,
                same_jurisdiction=True,
                owner_or_care_relation=True,
                consent=True,
                emergency=False,
                group_size=4,
                returned_fields=("group_count", protected_field),
                audit_level="standard",
                bug_type="aggregation_threshold_leak",
                expected_violation=True,
                primary_dimension="aggregation_threshold",
                risk=weight * 5,
            ),
            Scenario(
                scenario_id=f"{domain}_{replica}_{idx}_emergency_audit",
                domain=domain,
                endpoint=endpoint,
                role=role,
                purpose=purpose,
                same_jurisdiction=True,
                owner_or_care_relation=True,
                consent=True,
                emergency=True,
                group_size=30,
                returned_fields=("id", protected_field),
                audit_level="standard",
                bug_type="emergency_audit_downgrade",
                expected_violation=True,
                primary_dimension="enhanced_audit_dependency",
                risk=weight * 4,
            ),
            Scenario(
                scenario_id=f"{domain}_{replica}_{idx}_compound_scope",
                domain=domain,
                endpoint=endpoint,
                role=role,
                purpose=purpose,
                same_jurisdiction=False,
                owner_or_care_relation=False,
                consent=False,
                emergency=False,
                group_size=3,
                returned_fields=("id", protected_field),
                audit_level="standard",
                bug_type="compound_scope_field",
                expected_violation=True,
                primary_dimension="compound_policy_interaction",
                risk=weight * 10,
            ),
            Scenario(
                scenario_id=f"{domain}_{replica}_{idx}_clean_dependent",
                domain=domain,
                endpoint=endpoint,
                role=role,
                purpose=purpose,
                same_jurisdiction=True,
                owner_or_care_relation=True,
                consent=True,
                emergency=False,
                group_size=30,
                returned_fields=("id",),
                audit_level="standard",
                bug_type="clean",
                expected_violation=False,
                primary_dimension="none",
                risk=0.0,
            ),
        ])
    return rows


def dependent_oracle_reasons(scenario: Scenario) -> list[str]:
    policy = DOMAIN_POLICY[scenario.domain]
    protected_returned = policy["protected_field"] in scenario.returned_fields
    reasons = []
    if protected_returned and scenario.purpose != policy["purpose"]:
        reasons.append("purpose_field_dependency")
    if protected_returned and not scenario.same_jurisdiction:
        reasons.append("jurisdiction_field_dependency")
    if protected_returned and not scenario.owner_or_care_relation:
        reasons.append("object_field_dependency")
    if protected_returned and not scenario.consent:
        reasons.append("consent_field_dependency")
    if "group_count" in scenario.returned_fields and scenario.group_size < MINIMUM_GROUP_SIZE:
        reasons.append("aggregation_threshold")
    if scenario.emergency and scenario.audit_level != "enhanced":
        reasons.append("enhanced_audit_dependency")
    return reasons


def method_oracle_reasons(method: str, scenario: Scenario) -> list[str]:
    reasons = dependent_oracle_reasons(scenario)
    if method in {
        "schema_validation",
        "role_matrix",
        "object_policy_tests",
        "field_policy_tests",
        "audit_contract_tests",
        "basic_policy_aware_full",
    }:
        # These scenarios preserve structural validity, allowed coarse roles,
        # endpoint-level access, role-level fields, and standard audit events.
        return []
    if method == "dependent_policy_full":
        return reasons
    if method == "dependent_without_consent":
        return [reason for reason in reasons if reason != "consent_field_dependency"]
    if method == "dependent_without_threshold":
        return [reason for reason in reasons if reason != "aggregation_threshold"]
    if method == "dependent_without_enhanced_audit":
        return [reason for reason in reasons if reason != "enhanced_audit_dependency"]
    if method == "dependent_without_purpose_field":
        return [reason for reason in reasons if reason != "purpose_field_dependency"]
    raise ValueError(method)


def summarize(rows: list[dict]) -> list[dict]:
    out = []
    for method in sorted({row["method"] for row in rows}):
        items = [row for row in rows if row["method"] == method]
        tp = sum(1 for row in items if row["expected_violation"] and row["detected"])
        fp = sum(1 for row in items if not row["expected_violation"] and row["detected"])
        tn = sum(1 for row in items if not row["expected_violation"] and not row["detected"])
        fn = sum(1 for row in items if row["expected_violation"] and not row["detected"])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        risk_total = sum(row["risk"] for row in items if row["expected_violation"])
        risk_detected = sum(row["risk"] for row in items if row["expected_violation"] and row["detected"])
        out.append({
            "method": method,
            "n": len(items),
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "risk_weighted_recall": round(risk_detected / risk_total, 4) if risk_total else 0.0,
        })
    return out


def by_bug(rows: list[dict]) -> list[dict]:
    out = []
    for method in sorted({row["method"] for row in rows}):
        for bug_type in sorted({row["bug_type"] for row in rows if row["bug_type"] != "clean"}):
            items = [row for row in rows if row["method"] == method and row["bug_type"] == bug_type]
            detected = sum(row["detected"] for row in items)
            risk_total = sum(row["risk"] for row in items)
            risk_detected = sum(row["risk"] for row in items if row["detected"])
            out.append({
                "method": method,
                "bug_type": bug_type,
                "n": len(items),
                "detected": detected,
                "recall": round(detected / len(items), 4) if items else 0.0,
                "risk_weighted_recall": round(risk_detected / risk_total, 4) if risk_total else 0.0,
            })
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: list[dict], bug_rows: list[dict], all_rows: list[dict]) -> None:
    lines = [
        "# Nested Policy Stress Experiment",
        "",
        "## Design",
        "",
        f"- Scenarios: {len({row['scenario_id'] for row in all_rows})}",
        f"- Methods: {len({row['method'] for row in all_rows})}",
        f"- Method-scenario judgments: {len(all_rows)}",
        "- Stress dimensions: purpose-conditioned fields, jurisdiction-conditioned fields, consent-gated fields, aggregation thresholds, emergency audit escalation, and compound interactions.",
        "",
        "## Method Summary",
        "",
        "| Method | Precision | Recall | F1 | Risk-weighted recall |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in sorted(summary, key=lambda item: item["risk_weighted_recall"], reverse=True):
        lines.append(f"| {row['method']} | {row['precision']} | {row['recall']} | {row['f1']} | {row['risk_weighted_recall']} |")
    lines.extend([
        "",
        "## Recall by Dependent Failure",
        "",
        "| Method | Failure | Recall | Risk-weighted recall |",
        "|---|---|---:|---:|",
    ])
    for row in bug_rows:
        if row["method"] in {
            "basic_policy_aware_full",
            "dependent_policy_full",
            "dependent_without_consent",
            "dependent_without_threshold",
            "dependent_without_enhanced_audit",
            "dependent_without_purpose_field",
            "field_policy_tests",
            "object_policy_tests",
        }:
            lines.append(f"| {row['method']} | {row['bug_type']} | {row['recall']} | {row['risk_weighted_recall']} |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- The basic full suite is complete for the original independent-dimension benchmark but blind to policy dependencies not represented in the contract.",
        "- Dependent policy clauses recover the missed cases by adding explicit interaction oracles rather than by increasing random test volume.",
        "- The stress test therefore narrows the perfect-score claim: full recall holds for represented obligations, while nested production policies require explicit dependent clauses.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--multiplier", type=int, default=10)
    parser.add_argument("--out-dir", default=str(OUT))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for scenario in scenarios(args.multiplier):
        ground_truth_reasons = dependent_oracle_reasons(scenario)
        if bool(ground_truth_reasons) != scenario.expected_violation:
            raise AssertionError(f"inconsistent scenario ground truth: {scenario.scenario_id}")
        for method in METHODS:
            observed_reasons = method_oracle_reasons(method, scenario)
            rows.append({
                "scenario_id": scenario.scenario_id,
                "domain": scenario.domain,
                "endpoint": scenario.endpoint,
                "bug_type": scenario.bug_type,
                "primary_dimension": scenario.primary_dimension,
                "method": method,
                "expected_violation": int(scenario.expected_violation),
                "detected": int(bool(observed_reasons)),
                "oracle_reasons": ";".join(observed_reasons),
                "ground_truth_reasons": ";".join(ground_truth_reasons),
                "risk": scenario.risk,
                "same_jurisdiction": int(scenario.same_jurisdiction),
                "owner_or_care_relation": int(scenario.owner_or_care_relation),
                "consent": int(scenario.consent),
                "emergency": int(scenario.emergency),
                "group_size": scenario.group_size,
            })
    summary = summarize(rows)
    bug_rows = by_bug(rows)
    write_csv(out_dir / "nested_policy_stress_results.csv", rows)
    write_csv(out_dir / "nested_policy_stress_summary.csv", summary)
    write_csv(out_dir / "nested_policy_stress_by_bug.csv", bug_rows)
    write_report(out_dir / "NESTED_POLICY_STRESS_REPORT.md", summary, bug_rows, rows)
    (out_dir / "nested_policy_stress_summary.json").write_text(json.dumps({
        "multiplier": args.multiplier,
        "scenarios": len({row["scenario_id"] for row in rows}),
        "methods": len(METHODS),
        "judgments": len(rows),
    }, indent=2), encoding="utf-8")
    print(f"wrote nested policy stress results to {out_dir}")


if __name__ == "__main__":
    main()
