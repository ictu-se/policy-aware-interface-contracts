#!/usr/bin/env python3
"""Prompt-ablation experiment for local LLM policy judges."""

from __future__ import annotations

import argparse
import json
import socket
import urllib.error
from pathlib import Path

import run_llm_policy_judge as judge


PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "results" / "llm_prompt_ablation"


def minimal_prompt(case: dict) -> str:
    payload = {
        "task": "Decide whether the API response violates the policy contract.",
        "allowed_primary_dimension_values": judge.DIMENSION_CHOICES,
        "required_json": {
            "violation": "boolean",
            "primary_dimension": "one allowed value",
            "violation_reasons": "array of short strings",
            "confidence": "number from 0 to 1",
            "brief_reason": "one short sentence",
        },
        "policy_packet": {
            "domain": case["domain"],
            "endpoint": case["endpoint"],
            "operation": case["operation"],
            "resource": case["resource"],
            "policy": case["policy"],
            "request": case["request"],
            "response": case["response"],
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def checklist_prompt(case: dict) -> str:
    return judge.prompt_for(case)


def conservative_prompt(case: dict) -> str:
    payload = json.loads(judge.prompt_for(case))
    payload["false_positive_guard"] = (
        "Do not mark a violation only because sensitive fields exist in the policy. "
        "A field is a violation only when it appears in response.returned_fields and is not allowed for this actor role. "
        "If the response denies the request and no audit or inventory obligation is violated, use violation=false."
    )
    payload["attribution_guard"] = (
        "The primary dimension must name the earliest violated checklist item that is actually evidenced by the packet. "
        "For example, do not use field_minimization for a wrong-role denial unless extra returned fields are present."
    )
    return json.dumps(payload, ensure_ascii=False, indent=2)


PROMPTS = {
    "minimal": minimal_prompt,
    "checklist": checklist_prompt,
    "conservative": conservative_prompt,
}


def run_one(model: str, prompt_mode: str, args: argparse.Namespace) -> Path:
    safe_model = model.replace(":", "_").replace("/", "_")
    out_path = Path(args.out_dir) / f"{safe_model}__{prompt_mode}_policy_judge_outputs.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cases = judge.build_cases(args.seed, args.max_items, args.balanced)
    completed = set()
    if args.resume and out_path.exists():
        completed = {row["case_id"] for row in judge.load_jsonl(out_path)}

    prompt_builder = PROMPTS[prompt_mode]
    mode = "a" if args.resume else "w"
    count = 0
    with out_path.open(mode, encoding="utf-8", newline="\n") as out:
        for index, case in enumerate(cases, start=1):
            if case["case_id"] in completed:
                print(f"skip {model} {prompt_mode} {index}/{len(cases)} {case['case_id']}", flush=True)
                continue
            prompt = prompt_builder(case)
            try:
                result = judge.call_ollama(model, prompt, args.ollama_host, args.timeout, args.num_ctx, args.num_predict)
            except (TimeoutError, socket.timeout) as exc:
                result = {"returncode": -1, "stdout": "", "stderr": f"timeout: {exc}", "elapsed_sec": args.timeout, "eval_count": "", "prompt_eval_count": ""}
            except (urllib.error.URLError, json.JSONDecodeError, ConnectionError) as exc:
                result = {"returncode": -2, "stdout": "", "stderr": str(exc), "elapsed_sec": args.timeout, "eval_count": "", "prompt_eval_count": ""}
            parsed = judge.extract_json(result["stdout"])
            predicted_violation = judge.parse_bool(parsed.get("violation")) if parsed else 0
            predicted_dimension = judge.normalize_dimension(parsed.get("primary_dimension")) if parsed else "parse_error"
            record = {
                **case,
                "model": f"{model}|{prompt_mode}",
                "base_model": model,
                "prompt_mode": prompt_mode,
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
                f"{model} {prompt_mode} {index}/{len(cases)} {case['case_id']} "
                f"oracle={case['oracle_violation']}:{case['oracle_primary_dimension']} "
                f"pred={predicted_violation}:{predicted_dimension} elapsed={result['elapsed_sec']}",
                flush=True,
            )
    print(f"wrote {count} outputs to {out_path}")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=["qwen2.5-coder:14b", "gemma3:4b", "phi3:mini"])
    parser.add_argument("--prompt-modes", nargs="+", choices=sorted(PROMPTS), default=["minimal", "checklist", "conservative"])
    parser.add_argument("--out-dir", default=str(OUT))
    parser.add_argument("--max-items", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20260616)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--num-predict", type=int, default=512)
    parser.add_argument("--balanced", action="store_true", default=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    for model in args.models:
        for prompt_mode in args.prompt_modes:
            run_one(model, prompt_mode, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
