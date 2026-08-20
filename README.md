# Policy-Aware Interface Contracts

This is the clean replication package for the study **Policy-Aware Interface
Contracts for Testing Access-Control and Privacy Obligations in Service APIs**.
It contains experiment code, policy fixtures, protocols, and reported results.
It intentionally excludes manuscript sources, journal templates, letters, local
logs, caches, and submission files.

## Contents

- `scripts/`: compiler conformance, benchmark, stress checks, LLM scoring, and VAmPI case-study runner.
- `configs/`: machine-readable policy-contract schema.
- `data/`: benchmark cases and VAmPI policy contracts.
- `results/`: reported result tables and model outputs.
- `docs/`: experiment and judging protocols.
- `requirements.txt`: Python dependencies.

## Install

Python 3.9 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

The deterministic benchmark uses only the Python standard library. Matplotlib
is required only to regenerate the case-study figure.

## Controlled Benchmark

```bash
python3 scripts/main_experiment.py \
  --seed 20260616 \
  --multiplier 10 \
  --out-dir results/main_experiment_10x
```

This instantiates 12 semantic policy templates 10 times, producing 120
endpoints, 1,200 implementation variants, 1,080 injected faulty variants, and
79,200 method-specific execution findings. A mutation dispatcher materializes
label-free execution traces before any detector runs. Baseline oracles receive
only contracts, fixtures, implementation identifiers, and observed traces;
labels are joined only after findings are emitted to compute metrics.

## Contract Conformance

```bash
python3 scripts/contract_conformance.py \
  --contracts data/vampi_policy_contracts.json \
  --schema configs/policy_contract_schema.json \
  --out results/contract_conformance.json
```

The suite checks the five executable service contracts plus accepted and
rejected language cases. It covers required clauses, closed relation
operators, reference namespaces, non-empty role sets, aggregation bounds,
identifier uniqueness, adapter registration, lifecycle behavior, and
conflicting dependent requirements.

## Dependent-Policy and Benign-Variation Checks

```bash
python3 scripts/nested_policy_stress_experiment.py \
  --multiplier 10 \
  --out-dir results/nested_policy_stress_10x

python3 scripts/sensitivity_and_benign_stress.py \
  --seed 20260616 \
  --multiplier 10 \
  --out-dir results/sensitivity_and_benign_stress
```

## VAmPI OpenAPI Case Study

The case study uses VAmPI revision
`f16052dce83f05847133ec98f01c5193a41de7d8` in secure and vulnerable modes.
Docker and Docker Compose are required.

```bash
git clone https://github.com/erev0s/VAmPI.git
cd VAmPI
git checkout f16052dce83f05847133ec98f01c5193a41de7d8
docker build -t policy-vampi:study .
docker run -d --name policy-vampi-secure \
  -e vulnerable=0 -p 127.0.0.1:5001:5000 policy-vampi:study
docker run -d --name policy-vampi-vulnerable \
  -e vulnerable=1 -p 127.0.0.1:5002:5000 policy-vampi:study
cd ..

python3 scripts/vampi_case_study.py \
  --contracts data/vampi_policy_contracts.json \
  --schema configs/policy_contract_schema.json \
  --secure-base http://127.0.0.1:5001 \
  --vulnerable-base http://127.0.0.1:5002 \
  --out-dir results/vampi_case_study
```

The runner first validates and compiles the five machine-readable contracts,
rejecting unknown relation operators, unresolved operand namespaces, invalid
lifecycle combinations, conflicting requirements, and unregistered adapters
or oracles. It then resets both disposable
databases, executes the compiled checks, verifies three paired secure-mode
controls, and writes raw evidence signals, method-level findings, summary
metrics, and the data-derived figure. Each baseline consumes only its own
schema, credential, role, object, property, state, or inventory signals;
known-defect labels are joined only during scoring.

## Local LLM Scoring

Recorded outputs can be rescored without rerunning inference:

```bash
python3 scripts/score_llm_policy_judge.py \
  --results-dir results/llm_policy_judge

python3 scripts/score_llm_policy_judge.py \
  --results-dir results/llm_prompt_ablation
```

Rerunning inference requires Ollama and the model identifiers documented in
`docs/LLM_POLICY_JUDGE_PROTOCOL.md`.

## Reported Evidence

- Main benchmark: `results/main_experiment_10x/`
- Dependent-policy stress: `results/nested_policy_stress_10x/`
- Sensitivity and benign controls: `results/sensitivity_and_benign_stress/`
- Executable service case study: `results/vampi_case_study/`
- Local model judgments: `results/llm_policy_judge/` and `results/llm_prompt_ablation/`

## Data and Ethics

The controlled benchmark contains synthetic policies and responses. The VAmPI
study runs only the project's documented vulnerable-by-design service in local
disposable containers. No production service, personal data, or private API
trace is included.
