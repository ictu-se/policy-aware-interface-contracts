#!/usr/bin/env python3
"""Executable conformance checks for the policy-contract compiler."""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path

from vampi_case_study import compile_contracts


def write_document(directory: Path, name: str, document: dict) -> Path:
    path = directory / f"{name}.json"
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path


def expect_accept(name: str, document: dict, schema: Path, directory: Path) -> dict:
    path = write_document(directory, name, document)
    _, contracts = compile_contracts(path, schema)
    return {"case": name, "expected": "accept", "observed": "accept", "contracts": len(contracts)}


def expect_reject(name: str, document: dict, schema: Path, directory: Path) -> dict:
    path = write_document(directory, name, document)
    try:
        compile_contracts(path, schema)
    except ValueError as error:
        return {"case": name, "expected": "reject", "observed": "reject", "diagnostic": str(error)}
    raise AssertionError(f"{name}: compiler accepted an invalid contract")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contracts", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    source = json.loads(args.contracts.read_text(encoding="utf-8"))
    cases: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="policy-contract-conformance-") as temporary:
        directory = Path(temporary)
        cases.append(expect_accept("five_executable_contracts", source, args.schema, directory))

        dependent = copy.deepcopy(source)
        dependent["contracts"][0]["types"]["header.purpose"] = "String"
        dependent["contracts"][0]["dependent_clauses"] = [{
            "when": [{"operand": "header.purpose", "operator": "eq", "value": "research"}],
            "require": [
                {"obligation": "field", "value": "aggregate_only"},
                {"obligation": "audit", "value": "enhanced"},
            ],
        }]
        cases.append(expect_accept("conjunctive_dependent_requirements", dependent, args.schema, directory))

        missing_required = copy.deepcopy(source)
        del missing_required["contracts"][0]["authentication"]
        cases.append(expect_reject("missing_required_clause", missing_required, args.schema, directory))

        unknown_relation = copy.deepcopy(source)
        unknown_relation["contracts"][0]["object_scope"]["any_of"][0]["relation"] = "same_owner"
        cases.append(expect_reject("unknown_relation", unknown_relation, args.schema, directory))

        unresolved_reference = copy.deepcopy(source)
        unresolved_reference["contracts"][0]["object_scope"]["any_of"][0]["subject_operand"] = "owner"
        cases.append(expect_reject("unresolved_reference", unresolved_reference, args.schema, directory))

        type_mismatch = copy.deepcopy(source)
        type_mismatch["contracts"][0]["types"]["response.owner"] = "Integer"
        cases.append(expect_reject("predicate_type_mismatch", type_mismatch, args.schema, directory))

        unknown_resolver = copy.deepcopy(source)
        predicate = unknown_resolver["contracts"][0]["object_scope"]["any_of"][0]
        predicate["relation"] = "ancestor_of"
        predicate["resolver"] = "missing_hierarchy"
        cases.append(expect_reject("unregistered_hierarchy_resolver", unknown_resolver, args.schema, directory))

        empty_roles = copy.deepcopy(source)
        empty_roles["contracts"][0]["function_authorization"]["any_role"] = []
        cases.append(expect_reject("empty_role_set", empty_roles, args.schema, directory))

        invalid_threshold = copy.deepcopy(source)
        invalid_threshold["contracts"][0]["property_policy"]["aggregation"] = {
            "minimum_group_size": 1,
            "count_field": "group_count",
        }
        cases.append(expect_reject("invalid_aggregation_threshold", invalid_threshold, args.schema, directory))

        duplicate_id = copy.deepcopy(source)
        duplicate_id["contracts"][1]["id"] = duplicate_id["contracts"][0]["id"]
        cases.append(expect_reject("duplicate_contract_id", duplicate_id, args.schema, directory))

        unregistered_adapter = copy.deepcopy(source)
        unregistered_adapter["contracts"][0]["test"]["adapter"] = "missing_adapter"
        cases.append(expect_reject("unregistered_adapter", unregistered_adapter, args.schema, directory))

        invalid_inventory = copy.deepcopy(source)
        invalid_inventory["contracts"][0]["inventory"] = {
            "status": "deprecated",
            "behavior": "normal",
        }
        cases.append(expect_reject("inconsistent_inventory_behavior", invalid_inventory, args.schema, directory))

        conflicting = copy.deepcopy(dependent)
        conflicting["contracts"][0]["dependent_clauses"].append({
            "when": [{"operand": "header.purpose", "operator": "eq", "value": "research"}],
            "require": [{"obligation": "audit", "value": "standard"}],
        })
        cases.append(expect_reject("conflicting_dependent_requirements", conflicting, args.schema, directory))

    report = {
        "cases": len(cases),
        "passed": sum(case["expected"] == case["observed"] for case in cases),
        "results": cases,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
