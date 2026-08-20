# Experiment Plan

## Research Questions

- **RQ1:** Does the typed policy-contract profile compile declared role,
  object, jurisdiction, purpose, property, aggregation, audit, and lifecycle
  obligations into executable evidence?
- **RQ2:** Which represented policy faults are detected by independently
  executed structural, role, object, property, audit, inventory, and full
  policy-aware methods?
- **RQ3:** Does the profile expose documented VAmPI defects without alerting on
  the behaviors corrected by its secure configuration?
- **RQ4:** Can local language models reproduce the executable oracle's decision
  and primary fault dimension?

## Controlled Benchmark

The benchmark contains 12 semantic endpoint-policy templates instantiated 10
times with distinct identifiers. Each of the resulting 120 endpoints has one
correct implementation variant and nine injected faulty variants. Identifier
replication increases paired execution scale, not semantic diversity.

The mutation dispatcher materializes request/response traces before detection.
Each baseline receives its supported contract clauses, fixtures,
implementation identifier, and observed trace. Findings contain no injected
fault label. Labels are joined only after all findings have been generated.

## Dependent-Policy Stress

The stress experiment evaluates purpose-conditioned fields,
jurisdiction-conditioned fields, consent-gated fields, aggregation thresholds,
emergency audit escalation, and compound interactions. Its methods execute
predicate assertions over raw scenario state; no bug-to-capability lookup is
used.

## Executable Service Study

Five typed contracts are compiled and executed against local secure and
vulnerable VAmPI configurations. Evidence includes decisions, returned
properties, protected post-state, credential integrity, and endpoint
availability. Three behaviors corrected by secure mode serve as negative
controls. The study is descriptive and does not represent an industrial
deployment.

## Metrics

Reported metrics are precision, recall, F1, risk-weighted recall,
negative-control false-positive rate, and strict primary-dimension attribution
for the auxiliary LLM experiment. The compiler conformance suite reports
expected accept/reject outcomes for valid and invalid language constructs.
