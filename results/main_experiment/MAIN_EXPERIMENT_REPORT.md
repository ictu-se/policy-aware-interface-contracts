# Main Experiment Report

## Campaign

- Policies/endpoints: 12
- Variants: 120
- Injected buggy variants: 108
- Test cases: 108
- Test-level findings: 12960
- Elapsed seconds: 0.0506

## Primary Result

- Best method: `policy_aware_full`
- Recall: 1.0
- F1: 1.0
- Risk-weighted recall: 1.0

## Method Summary

| Method | Precision | Recall | F1 | Risk-weighted recall |
|---|---:|---:|---:|---:|
| policy_aware_full | 1.0 | 1.0 | 1.0 | 1.0 |
| full_without_audit | 1.0 | 0.8889 | 0.9412 | 0.9598 |
| full_without_purpose | 1.0 | 0.8889 | 0.9412 | 0.9464 |
| full_without_field_scope | 1.0 | 0.7778 | 0.875 | 0.8436 |
| full_without_object_scope | 1.0 | 0.7778 | 0.875 | 0.7992 |
| object_policy_tests | 1.0 | 0.4444 | 0.6154 | 0.6293 |
| role_matrix | 1.0 | 0.2222 | 0.3636 | 0.4285 |
| auth_required | 1.0 | 0.1111 | 0.2 | 0.2678 |
| field_policy_tests | 1.0 | 0.2222 | 0.3636 | 0.1564 |
| deprecated_inventory_tests | 1.0 | 0.1111 | 0.2 | 0.1205 |
| audit_contract_tests | 1.0 | 0.1111 | 0.2 | 0.0402 |
| schema_validation | 0.0 | 0.0 | 0.0 | 0.0 |

## Largest Baseline Miss Mechanisms

| Method | Bug type | Primary dimension | Recall | Risk missed |
|---|---|---|---:|---:|
| audit_contract_tests | missing_auth | authentication | 0.0 | 22800.0 |
| deprecated_inventory_tests | missing_auth | authentication | 0.0 | 22800.0 |
| field_policy_tests | missing_auth | authentication | 0.0 | 22800.0 |
| schema_validation | missing_auth | authentication | 0.0 | 22800.0 |
| audit_contract_tests | overbroad_role | function_authorization | 0.0 | 13680.0 |
| auth_required | overbroad_role | function_authorization | 0.0 | 13680.0 |
| deprecated_inventory_tests | overbroad_role | function_authorization | 0.0 | 13680.0 |
| field_policy_tests | overbroad_role | function_authorization | 0.0 | 13680.0 |
| schema_validation | overbroad_role | function_authorization | 0.0 | 13680.0 |
| audit_contract_tests | deprecated_exposed | endpoint_inventory | 0.0 | 10260.0 |
| auth_required | deprecated_exposed | endpoint_inventory | 0.0 | 10260.0 |
| field_policy_tests | deprecated_exposed | endpoint_inventory | 0.0 | 10260.0 |
| object_policy_tests | deprecated_exposed | endpoint_inventory | 0.0 | 10260.0 |
| role_matrix | deprecated_exposed | endpoint_inventory | 0.0 | 10260.0 |
| schema_validation | deprecated_exposed | endpoint_inventory | 0.0 | 10260.0 |
| audit_contract_tests | jurisdiction_bypass | jurisdiction_scope | 0.0 | 8550.0 |
| audit_contract_tests | missing_object_check | object_scope | 0.0 | 8550.0 |
| auth_required | jurisdiction_bypass | jurisdiction_scope | 0.0 | 8550.0 |

## Exposure Summary

| Bug type | Dimension | Events | Extra fields | Sensitive extra fields | Event risk |
|---|---|---:|---:|---:|---:|
| missing_auth | authentication | 12 | 96 | 76 | 663.0 |
| overbroad_role | function_authorization | 12 | 96 | 76 | 663.0 |
| jurisdiction_bypass | jurisdiction_scope | 12 | 67 | 53 | 553.0 |
| missing_object_check | object_scope | 12 | 67 | 53 | 553.0 |
| purpose_bypass | purpose_scope | 12 | 67 | 53 | 553.0 |
| missing_field_filter | field_minimization | 58 | 143 | 111 | 537.0 |
| missing_audit_log | audit_obligation | 108 | 0 | 0 | 324.0 |
| deprecated_exposed | endpoint_inventory | 12 | 29 | 23 | 158.0 |
| aggregation_leak | aggregation_boundary | 12 | 29 | 23 | 110.0 |

## Ablation Loss

| Ablation | Dimension | Bug type | Lost detections | Risk lost |
|---|---|---|---:|---:|
| full_without_object_scope | jurisdiction_scope | jurisdiction_bypass | 12 | 8550.0 |
| full_without_object_scope | object_scope | missing_object_check | 12 | 8550.0 |
| full_without_field_scope | field_minimization | missing_field_filter | 12 | 7400.0 |
| full_without_field_scope | aggregation_boundary | aggregation_leak | 12 | 5920.0 |
| full_without_purpose | purpose_scope | purpose_bypass | 12 | 4560.0 |
| full_without_audit | audit_obligation | missing_audit_log | 12 | 3420.0 |

## Main Interpretation

- Schema validation remains blind to policy bugs when responses are structurally valid.
- Role matrices detect coarse function authorization but miss object, jurisdiction, purpose, field, audit, and inventory obligations.
- Object-policy and field-policy tests each detect their own family but leave large missed-risk regions.
- The proposed suite is strongest because it combines decision, response-minimization, side-effect, and inventory oracles.

## Local LLM Policy-Judge Experiment

A separate Ollama experiment evaluated 11 local models on 120 shared balanced
policy-judge cases per model, for 1,320 total local LLM judgments. The raw
outputs and scoring tables are under `results/llm_policy_judge/`.

| Model | Decision acc. | Strict acc. | Recall | Risk recall |
|---|---:|---:|---:|---:|
| qwen2.5-coder:14b | 0.8333 | 0.4833 | 0.9074 | 0.875 |
| qwen2.5-coder:32b | 0.8 | 0.4667 | 0.8333 | 0.8151 |
| qwen2.5-coder:7b | 0.7 | 0.2917 | 0.75 | 0.8116 |
| gemma3:4b | 0.9 | 0.2833 | 1.0 | 1.0 |
| qwen2.5-coder:3b | 0.4167 | 0.2 | 0.4074 | 0.4793 |
| phi3:mini | 0.9 | 0.1917 | 1.0 | 1.0 |
| deepseek-coder:6.7b | 0.8083 | 0.1833 | 0.8889 | 0.9334 |
| qwen2.5:3b | 0.325 | 0.125 | 0.2963 | 0.3352 |
| llama3.2:3b | 0.7917 | 0.1167 | 0.8611 | 0.9272 |
| qwen2.5-coder:1.5b | 0.9 | 0.1 | 1.0 | 1.0 |
| qwen3:4b | 0.1 | 0.1 | 0.0 | 0.0 |

The LLM result separates detection from attribution: several local models flag
violations with high recall, but they often assign the wrong primary policy
dimension. The strongest strict attribution comes from qwen2.5-coder:14b and
qwen2.5-coder:32b. gemma3:4b strengthens the same pattern: it reaches full
recall but only 0.2833 strict accuracy, indicating over-triggering and weak
causal attribution.
