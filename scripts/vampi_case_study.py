#!/usr/bin/env python3
"""Compile policy contracts and execute their checks against two local VAmPI modes."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from jsonschema import Draft202012Validator


METHODS = (
    "schema_validation",
    "authentication_only",
    "role_matrix",
    "object_policy_tests",
    "property_policy_tests",
    "policy_aware_full",
)
RELATIONS = {"equal", "contains", "member_of", "ancestor_of"}
INVENTORY_STATES = {"active", "deprecated", "retired"}
REFERENCE_PREFIXES = (
    "caller.", "token.", "path.", "query.", "header.",
    "request.", "response.", "fixture.", "literal.",
)
ADAPTERS = {
    "cross_owner_book",
    "cross_subject_password_update",
    "admin_mass_assignment",
    "unauthenticated_debug_disclosure",
    "invalid_signature",
}
ORACLES = {
    "object_relation",
    "object_relation_and_post_state",
    "request_property_and_post_state",
    "authentication_response_and_inventory",
    "credential_integrity",
}
HIERARCHY_RESOLVERS = {"jurisdiction_hierarchy"}


def check_predicate_types(contract: dict, predicate: dict, operator_key: str = "relation") -> None:
    contract_id = contract["id"]
    operator = predicate[operator_key]
    left_key = "subject_operand" if operator_key == "relation" else "caller_operand"
    left = predicate[left_key]
    right = predicate["resource_operand"]
    types = contract.get("types", {})
    if left not in types or right not in types:
        missing = [operand for operand in (left, right) if operand not in types]
        raise ValueError(f"{contract_id}: missing type declaration for {missing}")
    signature = (types[left], types[right])
    allowed = {
        "equal": {("Bool", "Bool"), ("String", "String"), ("Integer", "Integer")},
        "contains": {("StringSet", "String")},
        "member_of": {("StringSet", "String")},
        "ancestor_of": {("String", "String")},
    }[operator]
    if signature not in allowed:
        raise ValueError(f"{contract_id}: invalid {operator} signature {signature}")
    if operator == "ancestor_of" and predicate.get("resolver") not in HIERARCHY_RESOLVERS:
        raise ValueError(f"{contract_id}: unregistered hierarchy resolver")


def validate_dependent_clauses(contract: dict) -> None:
    """Reject contradictory requirements under an identical guard."""
    requirements_by_guard: dict[str, dict[str, str]] = {}
    for clause in contract.get("dependent_clauses", []):
        guard = json.dumps(clause["when"], sort_keys=True)
        obligations = requirements_by_guard.setdefault(guard, {})
        for requirement in clause["require"]:
            obligation = requirement["obligation"]
            value = json.dumps(requirement["value"], sort_keys=True)
            previous = obligations.get(obligation)
            if previous is not None and previous != value:
                raise ValueError(
                    f"{contract.get('id')}: conflicting {obligation} requirements under one guard"
                )
            obligations[obligation] = value


def compile_contracts(path: Path, schema_path: Path) -> tuple[dict, list[dict]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    if document.get("schema_version") != "1.0":
        raise ValueError("unsupported contract schema_version")
    contracts = document.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        raise ValueError("contracts must be a non-empty array")

    seen = set()
    for contract in contracts:
        contract_id = contract.get("id")
        if not isinstance(contract_id, str) or not contract_id or contract_id in seen:
            raise ValueError(f"invalid or duplicate contract id: {contract_id!r}")
        seen.add(contract_id)

        errors = sorted(validator.iter_errors(contract), key=lambda error: list(error.path))
        if errors:
            location = ".".join(str(part) for part in errors[0].path) or "<root>"
            raise ValueError(f"{contract_id}: schema error at {location}: {errors[0].message}")

        operation = contract.get("operation", {})
        if operation.get("method") not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise ValueError(f"{contract_id}: invalid HTTP method")
        if not isinstance(operation.get("path"), str) or not operation["path"].startswith("/"):
            raise ValueError(f"{contract_id}: invalid operation path")

        authentication = contract.get("authentication", {})
        if not isinstance(authentication.get("required"), bool):
            raise ValueError(f"{contract_id}: authentication.required must be boolean")
        roles = contract.get("function_authorization", {}).get("any_role")
        if not isinstance(roles, list) or not roles or not all(isinstance(role, str) for role in roles):
            raise ValueError(f"{contract_id}: function_authorization.any_role must be strings")

        for predicate in contract.get("object_scope", {}).get("any_of", []):
            if predicate.get("relation") not in RELATIONS:
                raise ValueError(f"{contract_id}: unknown object relation")
            for key in ("subject_operand", "resource_operand"):
                operand = predicate.get(key)
                if not isinstance(operand, str) or not operand.startswith(REFERENCE_PREFIXES):
                    raise ValueError(f"{contract_id}: unresolved operand {operand!r}")
            check_predicate_types(contract, predicate)

        jurisdiction = contract.get("jurisdiction_scope")
        if jurisdiction:
            for key in ("caller_operand", "resource_operand"):
                operand = jurisdiction.get(key)
                if not isinstance(operand, str) or not operand.startswith(REFERENCE_PREFIXES):
                    raise ValueError(f"{contract_id}: unresolved operand {operand!r}")
            check_predicate_types(contract, jurisdiction, "comparator")

        for clause in contract.get("dependent_clauses", []):
            for condition in clause["when"]:
                operand = condition["operand"]
                if operand not in contract.get("types", {}):
                    raise ValueError(f"{contract_id}: missing type declaration for {operand}")

        state = contract.get("inventory", {}).get("status")
        if state not in INVENTORY_STATES:
            raise ValueError(f"{contract_id}: invalid inventory status")
        behavior = contract["inventory"]["behavior"]
        expected_behavior = {
            "active": "normal",
            "deprecated": "deprecation_header",
            "retired": "unavailable",
        }[state]
        if behavior != expected_behavior:
            raise ValueError(
                f"{contract_id}: inventory status {state} requires behavior {expected_behavior}"
            )
        validate_dependent_clauses(contract)
        test = contract.get("test", {})
        if test.get("adapter") not in ADAPTERS or test.get("oracle") not in ORACLES:
            raise ValueError(f"{contract_id}: unregistered adapter or oracle")
        if not isinstance(test.get("negative_fixture"), dict):
            raise ValueError(f"{contract_id}: negative_fixture must be an object")
        if not isinstance(test.get("secure_control"), bool):
            raise ValueError(f"{contract_id}: secure_control must be boolean")

    return document, contracts


def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def invalidly_signed_token(subject: str, key: str = "random") -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    now = int(time.time())
    payload = b64url(json.dumps({"exp": now + 3600, "iat": now, "sub": subject}, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = b64url(hmac.new(key.encode(), signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def request(base: str, method: str, path: str, body=None, token: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = raw
    return {"status": status, "body": parsed}


def login(base: str, username: str, password: str) -> str | None:
    response = request(base, "POST", "/users/v1/login", {"username": username, "password": password})
    body = response["body"] if isinstance(response["body"], dict) else {}
    return body.get("auth_token")


def reset(base: str) -> None:
    response = request(base, "GET", "/createdb")
    if response["status"] != 200:
        raise RuntimeError(f"database reset failed for {base}: {response}")


def book_owned_by(base: str, owner: str) -> str:
    response = request(base, "GET", "/books/v1")
    body = response["body"] if isinstance(response["body"], dict) else {}
    return next(item["book_title"] for item in body.get("Books", []) if item["user"] == owner)


def empty_signals() -> dict[str, bool]:
    return {
        "schema_mismatch": False,
        "authentication_violation": False,
        "credential_integrity_violation": False,
        "function_authorization_violation": False,
        "object_scope_violation": False,
        "request_property_violation": False,
        "response_property_violation": False,
        "forbidden_side_effect": False,
        "inventory_violation": False,
    }


def observation(contract: dict, mode: str, status: int, evidence: dict, signals: dict) -> dict:
    test = contract["test"]
    merged = empty_signals()
    merged.update(signals)
    return {
        "mode": mode,
        "test_case": contract["id"],
        "operation": f"{contract['operation']['method']} {contract['operation']['path']}",
        "oracle": test["oracle"],
        "known_defect": mode == "vulnerable" or not test["secure_control"],
        "secure_control": test["secure_control"],
        "violation_observed": any(merged.values()),
        "status": status,
        "signals": merged,
        "evidence": evidence,
    }


def execute_mode(base: str, mode: str, contracts: list[dict]) -> list[dict]:
    reset(base)
    token_name1 = login(base, "name1", "pass1")
    if not token_name1:
        raise RuntimeError(f"could not authenticate seeded user on {base}")

    rows = []
    for contract in contracts:
        adapter = contract["test"]["adapter"]
        if adapter == "cross_owner_book":
            title = book_owned_by(base, contract["test"]["negative_fixture"]["resource_owner"])
            response = request(base, "GET", f"/books/v1/{title}", token=token_name1)
            body = response["body"] if isinstance(response["body"], dict) else {}
            violated = response["status"] == 200 and body.get("owner") == "name2" and "secret" in body
            rows.append(observation(contract, mode, response["status"], {
                "owner": body.get("owner"), "secret_returned": "secret" in body,
            }, {"object_scope_violation": violated}))
        elif adapter == "cross_subject_password_update":
            changed = f"case-study-{mode}-pass"
            response = request(base, "PUT", "/users/v1/name2/password", {"password": changed}, token_name1)
            side_effect = login(base, "name2", changed) is not None
            rows.append(observation(contract, mode, response["status"], {
                "target_login_with_new_password": side_effect,
            }, {"object_scope_violation": side_effect, "forbidden_side_effect": side_effect}))
        elif adapter == "admin_mass_assignment":
            candidate = f"caseadmin_{mode}"
            response = request(base, "POST", "/users/v1/register", {
                "username": candidate, "password": "casepass",
                "email": f"{candidate}@example.test", "admin": True,
            })
            candidate_token = login(base, candidate, "casepass")
            current = request(base, "GET", "/me", token=candidate_token)
            body = current["body"] if isinstance(current["body"], dict) else {}
            created_admin = bool(body.get("data", {}).get("admin"))
            rows.append(observation(contract, mode, response["status"], {
                "registered_admin": created_admin,
            }, {"request_property_violation": created_admin, "forbidden_side_effect": created_admin}))
        elif adapter == "unauthenticated_debug_disclosure":
            response = request(base, "GET", "/users/v1/_debug")
            body = response["body"] if isinstance(response["body"], dict) else {}
            password_returned = any("password" in user for user in body.get("users", []))
            accepted = response["status"] == 200
            rows.append(observation(contract, mode, response["status"], {
                "password_field_returned": password_returned,
            }, {
                "authentication_violation": accepted,
                "function_authorization_violation": accepted,
                "response_property_violation": accepted and password_returned,
                "inventory_violation": accepted,
            }))
        elif adapter == "invalid_signature":
            response = request(base, "GET", "/me", token=invalidly_signed_token("admin"))
            body = response["body"] if isinstance(response["body"], dict) else {}
            accepted = response["status"] == 200 and body.get("data", {}).get("username") == "admin"
            rows.append(observation(contract, mode, response["status"], {
                "accepted_subject": body.get("data", {}).get("username"),
            }, {"credential_integrity_violation": accepted}))
        else:
            raise AssertionError(f"compiled adapter has no executor: {adapter}")
    return rows


def method_reasons(method: str, row: dict) -> list[str]:
    signals = row["signals"]
    if method == "schema_validation":
        keys = ("schema_mismatch",)
    elif method == "authentication_only":
        keys = ("authentication_violation", "credential_integrity_violation")
    elif method == "role_matrix":
        keys = ("function_authorization_violation",)
    elif method == "object_policy_tests":
        keys = ("object_scope_violation",)
    elif method == "property_policy_tests":
        keys = ("request_property_violation", "response_property_violation")
    elif method == "policy_aware_full":
        keys = tuple(signals)
    else:
        raise ValueError(method)
    return [key for key in keys if signals[key]]


def summarize(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    findings = []
    for row in rows:
        for method in METHODS:
            reasons = method_reasons(method, row)
            findings.append({
                "mode": row["mode"], "method": method,
                "test_case": row["test_case"], "oracle": row["oracle"],
                "known_defect": row["known_defect"],
                "secure_control": row["secure_control"],
                "detected": bool(reasons), "reasons": ";".join(reasons),
            })

    summary = []
    for method in METHODS:
        positives = [row for row in findings if row["mode"] == "vulnerable" and row["method"] == method]
        negatives = [
            row for row in findings
            if row["mode"] == "secure" and row["method"] == method and row["secure_control"]
        ]
        tp = sum(row["detected"] for row in positives)
        fp = sum(row["detected"] for row in negatives)
        summary.append({
            "method": method, "known_defects": len(positives), "tp": tp,
            "recall": round(tp / len(positives), 4),
            "negative_controls": len(negatives), "fp": fp,
            "false_positive_rate": round(fp / len(negatives), 4),
        })
    return findings, summary


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def make_figure(path: Path, summary: list[dict]) -> None:
    import matplotlib.pyplot as plt

    labels = [row["method"].replace("_", "\n") for row in summary]
    recall = [row["recall"] for row in summary]
    fpr = [row["false_positive_rate"] for row in summary]
    positions = list(range(len(labels)))
    width = 0.38
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    ax.bar([p - width / 2 for p in positions], recall, width, label="Known-defect recall", color="#2b6f9f")
    ax.bar([p + width / 2 for p in positions], fpr, width, label="Negative-control FPR", color="#d28b3c")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Rate")
    ax.set_xticks(positions, labels, fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=2, loc="upper left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contracts", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--secure-base", default="http://127.0.0.1:5001")
    parser.add_argument("--vulnerable-base", default="http://127.0.0.1:5002")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    document, contracts = compile_contracts(args.contracts, args.schema)
    observations = execute_mode(args.secure_base, "secure", contracts)
    observations.extend(execute_mode(args.vulnerable_base, "vulnerable", contracts))
    findings, summary = summarize(observations)
    write_csv(args.out_dir / "vampi_observations.csv", [{
        **{key: value for key, value in row.items() if key not in {"signals", "evidence"}},
        "signals": json.dumps(row["signals"], sort_keys=True),
        "evidence": json.dumps(row["evidence"], sort_keys=True),
    } for row in observations])
    write_csv(args.out_dir / "vampi_findings.csv", findings)
    write_csv(args.out_dir / "vampi_method_summary.csv", summary)
    (args.out_dir / "vampi_case_study.json").write_text(json.dumps({
        "source_revision": document["source_revision"],
        "contract_schema_version": document["schema_version"],
        "contract_ids": [contract["id"] for contract in contracts],
        "secure_base": args.secure_base, "vulnerable_base": args.vulnerable_base,
        "observations": observations, "summary": summary,
    }, indent=2), encoding="utf-8")
    make_figure(args.out_dir / "fig_vampi_case_study.pdf", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
