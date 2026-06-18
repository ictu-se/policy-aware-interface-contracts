# Policy-Aware Interface Contracts

This repository is the replication package for the study:

**Policy-Aware Interface Contracts for Testing Access-Control and Privacy
Obligations in Service APIs**

The package contains the benchmark generator, policy-contract schema, generated
cases, experiment scripts, and result tables used for the manuscript. It does
not contain manuscript source files, journal templates, cover letters, or local
submission artifacts.

## Repository Contents

- `scripts/`: executable benchmark and analysis scripts.
- `configs/`: JSON schema for policy-aware API contracts.
- `data/`: generated policy variants and policy test cases.
- `results/`: reproduced result tables and raw local LLM outputs used for
  scoring.
- `docs/`: experiment protocols.
- `requirements.txt`: dependency note. The deterministic benchmark uses only
  the Python standard library.
- `MANIFEST.md`: traceability map for included artifacts.
- `LICENSE`: reuse terms for the replication package.

## Runtime and Archival Status

The deterministic benchmark was verified with Python 3.9.6 and uses only the
Python standard library. Local LLM inference was run with Ollama 0.30.7. The
raw LLM outputs included in this repository are the reproducibility source for
reported model scores, because local model decoding can vary across runtime
and model revisions.

This GitHub repository is the current public replication package. A versioned
GitHub release and external archival DOI can be added after journal submission
or acceptance; no DOI is claimed here.

## Deterministic Benchmark

Run the 10-fold policy-aware contract benchmark:

```bash
python3 scripts/policy_contract_benchmark.py \
  --seed 20260616 \
  --multiplier 10 \
  --out-dir results/benchmark_10x
```

This reproduces the 120-policy benchmark scale:

- 120 endpoint policies;
- 1,200 implementation variants;
- 1,080 injected buggy variants;
- 10,800 generated test executions per method;
- 129,600 test-level findings across all methods.

## Main Experiment Tables

Run the paper-facing main experiment:

```bash
python3 scripts/main_experiment.py \
  --seed 20260616 \
  --multiplier 10 \
  --out-dir results/main_experiment_10x
```

The key outputs are:

- `results/main_experiment_10x/method_summary.csv`
- `results/main_experiment_10x/exposure_summary.csv`
- `results/main_experiment_10x/ablation_loss.csv`
- `results/main_experiment_10x/baseline_failure_mechanisms.csv`
- `results/main_experiment_10x/MAIN_EXPERIMENT_REPORT.md`

## Dependent-Policy Stress Experiment

Run the dependent-policy stress test:

```bash
python3 scripts/nested_policy_stress_experiment.py \
  --multiplier 10 \
  --out-dir results/nested_policy_stress_10x
```

This reproduces 280 dependent-policy scenarios and 3,080
method-scenario judgments.

## Risk Sensitivity and Benign-Variation Stress

Run the additional validation checks:

```bash
python3 scripts/sensitivity_and_benign_stress.py \
  --seed 20260616 \
  --multiplier 10 \
  --out-dir results/sensitivity_and_benign_stress
```

This reproduces:

- five risk-weighting schemes: equal, severity-only, current, privacy-heavy,
  and audit/inventory-heavy;
- the full suite's rank-1 weighted recall under all five schemes;
- 4,440 benign policy-compliant response variants with zero false positives.

## Local LLM Policy-Judge Experiments

The repository includes the raw local model outputs used for scoring. To
recompute the score tables from existing outputs:

```bash
python3 scripts/score_llm_policy_judge.py \
  --results-dir results/llm_policy_judge

python3 scripts/score_llm_policy_judge.py \
  --results-dir results/llm_prompt_ablation
```

To rerun local model inference, install and run Ollama with the model names
listed in `docs/LLM_POLICY_JUDGE_PROTOCOL.md`, then run:

```bash
MAX_ITEMS=120 TIMEOUT=300 bash scripts/run_llm_policy_judge_matrix.sh

python3 scripts/run_llm_prompt_ablation.py \
  --max-items 120 \
  --balanced \
  --out-dir results/llm_prompt_ablation
```

LLM inference is not deterministic across all model/runtime versions. The
included JSONL outputs are the source used to reproduce the reported score
tables.

The fixed-prompt run used these Ollama model identifiers where available in the
local runtime:

- `deepseek-coder:6.7b` (`ce298d984115`)
- `gemma3:4b` (`a2af6cc3eb7f`)
- `llama3.2:3b` (`a80c4f17acd5`)
- `phi3:mini` (`4f2222927938`)
- `qwen2.5-coder:1.5b` (`d7372fd82851`)
- `qwen2.5-coder:3b` (`f72c60cabf62`)
- `qwen2.5-coder:7b` (`dae161e27b0e`)
- `qwen2.5-coder:14b` (`9ec8897f747e`)
- `qwen2.5-coder:32b` (`b92d6a0bd47e`)
- `qwen2.5:3b` (`357c53fb659c`)
- `qwen3:4b` (`359d7dd4bcda`)

## Quick Verification

The following commands should complete without third-party Python packages:

```bash
python3 scripts/policy_contract_benchmark.py --seed 20260616 --multiplier 10 --out-dir /tmp/policy_contract_benchmark_10x
python3 scripts/main_experiment.py --seed 20260616 --multiplier 10 --out-dir /tmp/main_experiment_10x
python3 scripts/nested_policy_stress_experiment.py --multiplier 10 --out-dir /tmp/nested_policy_stress_10x
python3 scripts/sensitivity_and_benign_stress.py --seed 20260616 --multiplier 10 --out-dir /tmp/sensitivity_and_benign_stress
python3 scripts/score_llm_policy_judge.py --results-dir results/llm_policy_judge
python3 scripts/score_llm_policy_judge.py --results-dir results/llm_prompt_ablation
```

These commands regenerate the deterministic benchmark tables and rescore the
included LLM outputs. On a typical laptop, the deterministic checks complete in
minutes; rerunning local LLM inference is intentionally excluded from the quick
path.

## Figure and Table Traceability

- Manuscript Table 1: conformance levels defined in the manuscript and schema.
- Manuscript Table 2: policy dimensions defined in the manuscript and schema.
- Manuscript Table 3: `results/main_experiment_10x/main_experiment_summary.json`.
- Manuscript Table 4: `results/nested_policy_stress_10x/nested_policy_stress_summary.csv`.
- Figure 1: `results/main_experiment_10x/policy_detection_results.csv`,
  `results/main_experiment_10x/exposure_summary.csv`, and
  `results/main_experiment_10x/first_detection_triggers.csv`.
- Figure 2: `results/main_experiment_10x/method_summary.csv`,
  `results/sensitivity_and_benign_stress/risk_weight_sensitivity.csv`,
  `results/sensitivity_and_benign_stress/benign_variation_summary.csv`, and
  `results/nested_policy_stress_10x/nested_policy_stress_summary.csv`.
- Figure 3: `results/main_experiment_10x/recall_by_bug_family.csv`.
- Figure 4: `results/main_experiment_10x/exposure_summary.csv`.
- Figure 5: `results/main_experiment_10x/ablation_loss.csv`.
- Figure 6: `results/llm_policy_judge/llm_policy_judge_summary.csv`.
- Figure 7: `results/llm_policy_judge/llm_policy_judge_by_group.csv`.
- Figure 8: `results/llm_prompt_ablation/llm_policy_judge_summary.csv`.

## Data Ethics

All benchmark policies, API responses, and test cases are synthetic. The package
does not include personal data or production API traces.
