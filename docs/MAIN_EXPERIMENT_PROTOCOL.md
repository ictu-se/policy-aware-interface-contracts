# Main Experiment Protocol

## Purpose

The main experiment evaluates policy-aware contract testing through causal
mechanisms, not repeated random seeds. Each result table must answer why a
method detects or misses a policy bug.

## Research Questions Covered

- **RQ1:** How much detection coverage does each method obtain?
- **RQ2:** Which policy-bug families are missed by structural, role-only, and
  single-dimension baselines?
- **RQ3:** Which missing contract dimension explains each false negative?
- **RQ4:** How much sensitive-field exposure and event-level risk does each bug
  family create?
- **RQ5:** Which full-suite ablation loses which bug family?
- **RQ6:** Which generated test kind first triggers detection?

## Ground Truth

Ground truth is deterministic bug injection. Each endpoint has one correct
variant and nine buggy variants. The injected bug type defines the expected
fault family and primary missing contract dimension.

## Methods

The campaign compares:

- schema validation;
- authentication-required check;
- role matrix;
- object-policy tests;
- field-policy tests;
- audit contract tests;
- deprecated endpoint inventory tests;
- full policy-aware contract tests;
- full-suite ablations without object scope, field scope, audit, or purpose.

## Main Outputs

The campaign writes outputs to `results/main_experiment/`:

- `method_summary.csv`: precision, recall, F1, and risk-weighted recall.
- `recall_by_bug_family.csv`: method recall by policy-bug family.
- `baseline_failure_mechanisms.csv`: baseline misses by bug type and primary
  dimension.
- `causal_miss_analysis.csv`: false negatives with oracle evidence.
- `causal_miss_summary.csv`: false negatives grouped by root cause.
- `first_detection_triggers.csv`: the first generated test kind that detects
  each bug.
- `exposure_events.csv`: event-level violation and field-exposure evidence.
- `exposure_summary.csv`: aggregate exposure by bug family.
- `ablation_loss.csv`: detections and risk lost by each ablation.
- `casebook.csv`: representative examples explaining each miss mechanism.
- `MAIN_EXPERIMENT_REPORT.md`: human-readable report for manuscript drafting.

## Run Command

```bash
python3 scripts/main_experiment.py
```

## Interpretation Rule

A longer runtime is not evidence by itself. A new experiment should be added
only when it isolates a mechanism: missing subject-resource predicate, missing
purpose constraint, missing response minimization, missing aggregate boundary,
missing audit side effect, or stale endpoint inventory.
