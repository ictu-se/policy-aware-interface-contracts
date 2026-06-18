#!/usr/bin/env python3
"""Run local Ollama models as policy-violation judges.

The deterministic benchmark remains the ground truth. This experiment tests
whether local LLMs can infer the same violation decision and primary policy
dimension from a compact policy/request/response/audit evidence packet.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

import policy_contract_benchmark as bench


PROJECT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT / "results"
PROMPTS = PROJECT / "prompts"
csv_safe_limit = getattr(sys, "maxsize", 2**31 - 1)

SYSTEM = (
    "You are a policy-aware API contract auditor. Return strict JSON only. "
    "Use only the given policy, request, response, and audit evidence. "
    "Do not use outside assumptions."
)

DIMENSION_CHOICES = [
    "none",
    "authentication",
    "function_authorization",
    "object_scope",
    "jurisdiction_scope",
    "purpose_scope",
    "field_minimization",
    "aggregation_boundary",
    "audit_obligation",
    "endpoint_inventory",
]


def clean(text: str) -> str:
    text = text or ""
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def extract_json(text: str) -> dict | None:
    text = clean(text)
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            value = json.loads(text[start:end + 1])
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def load_jsonl(path: Path):
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def call_ollama(model: str, prompt: str, host: str, timeout: int, num_ctx: int, num_predict: int) -> dict:
    started = time.time()
    payload = {
        "model": model,
        "prompt": SYSTEM + "\n\n" + prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "top_p": 1,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    request = urllib.request.Request(
        host.rstrip("/") + "/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8", errors="replace"))
    return {
        "returncode": 0,
        "stdout": clean(body.get("response", "")),
        "stderr": "",
        "elapsed_sec": round(time.time() - started, 3),
        "eval_count": body.get("eval_count", ""),
        "prompt_eval_count": body.get("prompt_eval_count", ""),
    }


def fields_by_sensitivity(policy: bench.EndpointPolicy) -> dict[str, list[str]]:
    out = defaultdict(list)
    for field in policy.fields:
        out[field.sensitivity].append(field.name)
    return {key: sorted(value) for key, value in sorted(out.items())}


def make_case_id(variant: bench.Variant, test: bench.TestCase) -> str:
    return f"{variant.variant_id}::{test.test_id.rsplit('::', 1)[-1]}"


def response_for_prompt(response: bench.Response, test: bench.TestCase) -> dict:
    return {
        "allowed": response.allowed,
        "returned_fields": list(response.fields),
        "requested_fields": list(test.requested_fields),
        "audit_logged": response.audit_logged,
        "deprecated_endpoint_available": response.deprecated_available,
    }


def build_cases(seed: int, max_items: int, balanced: bool) -> list[dict]:
    rng = random.Random(seed)
    policies = bench.domains()
    policy_map = {bench.policy_id(policy): policy for policy in policies}
    variants = bench.make_variants(policies)
    tests_by_policy = {bench.policy_id(policy): bench.make_tests(policy, rng) for policy in policies}
    cases = []
    for variant in variants:
        policy = policy_map[variant.policy_id]
        for test in tests_by_policy[variant.policy_id]:
            response = bench.apply_variant(policy, variant.bug_type, test)
            violation, reasons, risk = bench.expected_violation(policy, test, response)
            primary_dimension = bench.PRIMARY_DIMENSION_BY_BUG.get(variant.bug_type, "none") if violation else "none"
            case = {
                "case_id": make_case_id(variant, test),
                "domain": policy.domain,
                "endpoint": policy.endpoint,
                "operation": policy.operation,
                "resource": policy.resource,
                "bug_type": variant.bug_type,
                "family": variant.family,
                "test_kind": test.test_kind,
                "oracle_violation": int(violation),
                "oracle_reasons": reasons,
                "oracle_primary_dimension": primary_dimension,
                "oracle_risk": round(risk, 4),
                "policy": {
                    "roles": list(policy.roles),
                    "purposes": list(policy.purposes),
                    "object_scope": policy.object_scope,
                    "fields_by_sensitivity": fields_by_sensitivity(policy),
                    "allowed_fields_for_actor_role": list(bench.allowed_fields(policy, test.actor)),
                    "audit_required": policy.audit_required,
                    "deprecated": policy.deprecated,
                },
                "request": {
                    "actor_role": test.actor.role,
                    "actor_authenticated": test.actor.authenticated,
                    "actor_jurisdiction": test.actor.jurisdiction,
                    "actor_subject_id": test.actor.subject_id,
                    "purpose": test.actor.purpose,
                    "resource_owner_id": test.obj.owner_id,
                    "resource_jurisdiction": test.obj.jurisdiction,
                    "requested_fields": list(test.requested_fields),
                },
                "response": response_for_prompt(response, test),
            }
            cases.append(case)

    if balanced:
        by_dimension = defaultdict(list)
        for case in cases:
            by_dimension[case["oracle_primary_dimension"]].append(case)
        selected = []
        per_bucket = max(1, max_items // max(1, len(by_dimension))) if max_items else 0
        for _, bucket in sorted(by_dimension.items()):
            bucket = list(bucket)
            rng.shuffle(bucket)
            selected.extend(bucket[:per_bucket] if max_items else bucket)
        if max_items and len(selected) < max_items:
            remaining = [case for case in cases if case not in selected]
            rng.shuffle(remaining)
            selected.extend(remaining[: max_items - len(selected)])
        cases = selected[:max_items] if max_items else selected
    else:
        rng.shuffle(cases)
        if max_items:
            cases = cases[:max_items]
    return sorted(cases, key=lambda item: item["case_id"])


def prompt_for(case: dict) -> str:
    instruction = {
        "task": "Judge whether this API response violates the policy contract.",
        "required_output": (
            "Return exactly one JSON object. The field primary_dimension must be exactly one string, "
            "not a list. Allowed primary_dimension values are: " + ", ".join(DIMENSION_CHOICES) + "."
        ),
        "json_keys": ["violation", "primary_dimension", "violation_reasons", "confidence", "brief_reason"],
        "policy_packet": {
            "domain": case["domain"],
            "endpoint": case["endpoint"],
            "operation": case["operation"],
            "resource": case["resource"],
            "policy": case["policy"],
            "request": case["request"],
            "response": case["response"],
        },
        "decision_checklist_in_order": {
            "authentication": "If actor_authenticated is false and response.allowed is true, violation=true.",
            "function_authorization": "If actor_role is not in policy.roles and response.allowed is true, violation=true.",
            "purpose_scope": "If purpose is not in policy.purposes and response.allowed is true, violation=true.",
            "object_or_jurisdiction_scope": "If actor and purpose are otherwise valid but actor_jurisdiction does not match resource_jurisdiction, response.allowed may violate object_scope unless the actor is a permitted self/owner/public case.",
            "field_minimization": "Only compare response.returned_fields against policy.allowed_fields_for_actor_role. Requested fields that are omitted from the response are not a violation.",
            "audit_obligation": "If policy.audit_required is true and response.audit_logged is false, violation=true.",
            "endpoint_inventory": "If response.deprecated_endpoint_available is true, violation=true.",
            "none": "If none of the checks above fire, set violation=false and primary_dimension=none.",
        },
        "primary_dimension_rule": (
            "When multiple checks fire, choose the first applicable primary dimension in checklist order. "
            "Do not invent dimensions or return multiple dimensions."
        ),
    }
    return json.dumps(instruction, ensure_ascii=False, indent=2)


def parse_bool(value) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(bool(value))
    if isinstance(value, str):
        return int(value.strip().lower() in {"true", "1", "yes"})
    return 0


def normalize_dimension(value) -> str:
    if isinstance(value, list):
        for item in value:
            normalized = normalize_dimension(item)
            if normalized in DIMENSION_CHOICES:
                return normalized
        return "unknown"
    if not isinstance(value, str):
        return "unknown"
    value = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "authorization": "function_authorization",
        "object_authorization": "object_scope",
        "jurisdiction": "jurisdiction_scope",
        "purpose": "purpose_scope",
        "field_filtering": "field_minimization",
        "privacy": "field_minimization",
        "audit": "audit_obligation",
        "inventory": "endpoint_inventory",
        "deprecated_endpoint": "endpoint_inventory",
        "no_violation": "none",
    }
    return aliases.get(value, value if value in DIMENSION_CHOICES else "unknown")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument("--max-items", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260616)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--num-predict", type=int, default=512)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--balanced", action="store_true")
    args = parser.parse_args()

    safe_model = args.model.replace(":", "_").replace("/", "_")
    out_path = Path(args.out) if args.out else RESULTS / "llm_policy_judge" / f"{safe_model}_policy_judge_outputs.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cases = build_cases(args.seed, args.max_items, args.balanced)

    completed = set()
    if args.resume and out_path.exists():
        completed = {row["case_id"] for row in load_jsonl(out_path)}

    mode = "a" if args.resume else "w"
    count = 0
    with out_path.open(mode, encoding="utf-8", newline="\n") as out:
        for index, case in enumerate(cases, start=1):
            if case["case_id"] in completed:
                print(f"skip {index}/{len(cases)} {case['case_id']}", flush=True)
                continue
            prompt = prompt_for(case)
            try:
                result = call_ollama(args.model, prompt, args.ollama_host, args.timeout, args.num_ctx, args.num_predict)
            except (TimeoutError, socket.timeout) as exc:
                result = {"returncode": -1, "stdout": "", "stderr": f"timeout: {exc}", "elapsed_sec": args.timeout, "eval_count": "", "prompt_eval_count": ""}
            except (urllib.error.URLError, json.JSONDecodeError, ConnectionError) as exc:
                result = {"returncode": -2, "stdout": "", "stderr": str(exc), "elapsed_sec": args.timeout, "eval_count": "", "prompt_eval_count": ""}
            parsed = extract_json(result["stdout"])
            predicted_violation = parse_bool(parsed.get("violation")) if parsed else 0
            predicted_dimension = normalize_dimension(parsed.get("primary_dimension")) if parsed else "parse_error"
            record = {
                **case,
                "model": args.model,
                **result,
                "parse_ok": int(parsed is not None),
                "predicted_violation": predicted_violation,
                "predicted_primary_dimension": predicted_dimension,
                "predicted_reasons": parsed.get("violation_reasons", []) if parsed else [],
                "predicted_confidence": parsed.get("confidence", "") if parsed else "",
                "predicted_brief_reason": parsed.get("brief_reason", "") if parsed else "",
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            count += 1
            print(
                f"{index}/{len(cases)} {case['case_id']} "
                f"oracle={case['oracle_violation']}:{case['oracle_primary_dimension']} "
                f"pred={predicted_violation}:{predicted_dimension} "
                f"rc={result['returncode']} elapsed={result['elapsed_sec']}",
                flush=True,
            )
    print(f"wrote {count} outputs to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
