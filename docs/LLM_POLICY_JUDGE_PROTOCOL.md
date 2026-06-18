# Local LLM Policy-Judge Experiment

## Purpose

This experiment evaluates whether local Ollama models can act as policy-aware
judges for API contract violations. The deterministic policy oracle remains
the ground truth.

The key distinction is between:

- detecting that a violation exists; and
- attributing the violation to the correct primary policy dimension.

## Task

Each model receives a compact JSON policy packet containing:

- endpoint, operation, and resource;
- allowed roles and purposes;
- object-scope rule name;
- field sensitivities;
- allowed fields for the actor role;
- request actor, purpose, jurisdiction, subject, and requested fields;
- response allow/deny decision, returned fields, audit flag, and deprecated
  endpoint availability.

The model must return strict JSON with:

- `violation`;
- `primary_dimension`;
- `violation_reasons`;
- `confidence`;
- `brief_reason`.

## Models

The fixed-prompt run used 11 local Ollama models:

- `qwen2.5-coder:1.5b`
- `qwen2.5-coder:3b`
- `qwen2.5-coder:7b`
- `qwen2.5-coder:14b`
- `qwen2.5-coder:32b`
- `deepseek-coder:6.7b`
- `gemma3:4b`
- `qwen2.5:3b`
- `qwen3:4b`
- `llama3.2:3b`
- `phi3:mini`

Each model was evaluated on 120 balanced policy-judge cases, for 1,320 fixed
prompt local LLM judgments. The prompt-ablation experiment adds 1,080
judgments across three representative models and three prompt modes, yielding
2,400 judgments across the full LLM study.

## Commands

Run one model:

```bash
python3 scripts/run_llm_policy_judge.py --model qwen2.5-coder:7b --max-items 120 --balanced --resume
```

Run the matrix:

```bash
MAX_ITEMS=120 TIMEOUT=300 bash scripts/run_llm_policy_judge_matrix.sh
```

Score outputs:

```bash
python3 scripts/score_llm_policy_judge.py --results-dir results/llm_policy_judge
```

## Outputs

The experiment writes to `results/llm_policy_judge/`:

- one raw JSONL output file per model;
- `llm_policy_judge_scored.csv`;
- `llm_policy_judge_summary.csv`;
- `llm_policy_judge_by_group.csv`;
- `LLM_POLICY_JUDGE_SUMMARY.md`.

## Main Finding

Several local models identify violations with high recall, but strict causal
attribution remains much harder. Smaller models often over-trigger one generic
dimension. Larger Qwen coder models improve strict attribution, but still tend
to collapse aggregation, endpoint inventory, object scope, and jurisdiction
scope into field minimization. `qwen3:4b` failed the required JSON format in
this prompt configuration.
