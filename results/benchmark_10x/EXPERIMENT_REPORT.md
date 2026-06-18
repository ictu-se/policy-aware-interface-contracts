# Policy-Aware Contract Testing Experiment Report

## Benchmark Size

- Policies/endpoints: 120
- Variants: 1200
- Injected buggy variants: 1080
- Test cases per endpoint: 9
- Total test executions per method: 10800

## Bug Families

- auditability: 120
- function_auth: 240
- inventory: 120
- object_auth: 240
- property_auth: 240
- purpose_scope: 120

## Policy-Aware Recall by Domain

| Domain | Variants | Recall | Risk-weighted recall |
|---|---:|---:|---:|
| business_licensing | 270 | 1.0 | 1.0 |
| citizen_services | 270 | 1.0 | 1.0 |
| education | 270 | 1.0 | 1.0 |
| health | 270 | 1.0 | 1.0 |

## Best Method

- Method: `policy_aware_full`
- Precision: 1.0
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

## Test Budget Curve

| Suite | Method | Tests per endpoint | Recall | Risk-weighted recall |
|---|---|---:|---:|---:|
| auth_smoke | policy_aware_full | 2 | 0.3333 | 0.3949 |
| privacy_scope | policy_aware_full | 3 | 0.3333 | 0.1966 |
| role_matrix_min | policy_aware_full | 3 | 0.4444 | 0.5556 |
| object_scope | policy_aware_full | 5 | 0.6667 | 0.7564 |
| purpose_object_scope | policy_aware_full | 6 | 0.7778 | 0.81 |
| no_inventory | policy_aware_full | 8 | 0.8889 | 0.8795 |
| full | policy_aware_full | 9 | 1.0 | 1.0 |

## Causal Miss Summary

| Method | Root cause | Primary missing dimension | Missed variants | Risk missed |
|---|---|---|---:|---:|
| audit_contract_tests | missing_authentication_oracle | authentication | 120 | 228000.0 |
| deprecated_inventory_tests | missing_authentication_oracle | authentication | 120 | 228000.0 |
| field_policy_tests | missing_authentication_oracle | authentication | 120 | 228000.0 |
| schema_validation | missing_authentication_oracle | authentication | 120 | 228000.0 |
| audit_contract_tests | missing_function_authorization_oracle | function_authorization | 120 | 136800.0 |
| auth_required | missing_function_authorization_oracle | function_authorization | 120 | 136800.0 |
| deprecated_inventory_tests | missing_function_authorization_oracle | function_authorization | 120 | 136800.0 |
| field_policy_tests | missing_function_authorization_oracle | function_authorization | 120 | 136800.0 |
| schema_validation | missing_function_authorization_oracle | function_authorization | 120 | 136800.0 |
| audit_contract_tests | missing_endpoint_inventory_oracle | endpoint_inventory | 120 | 102600.0 |
| auth_required | missing_endpoint_inventory_oracle | endpoint_inventory | 120 | 102600.0 |
| field_policy_tests | missing_endpoint_inventory_oracle | endpoint_inventory | 120 | 102600.0 |
| object_policy_tests | missing_endpoint_inventory_oracle | endpoint_inventory | 120 | 102600.0 |
| role_matrix | missing_endpoint_inventory_oracle | endpoint_inventory | 120 | 102600.0 |
| schema_validation | missing_endpoint_inventory_oracle | endpoint_inventory | 120 | 102600.0 |
| audit_contract_tests | missing_jurisdiction_predicate | jurisdiction_scope | 120 | 85500.0 |
| audit_contract_tests | missing_object_scope_predicate | object_scope | 120 | 85500.0 |
| auth_required | missing_jurisdiction_predicate | jurisdiction_scope | 120 | 85500.0 |
| auth_required | missing_object_scope_predicate | object_scope | 120 | 85500.0 |
| deprecated_inventory_tests | missing_jurisdiction_predicate | jurisdiction_scope | 120 | 85500.0 |
| deprecated_inventory_tests | missing_object_scope_predicate | object_scope | 120 | 85500.0 |
| field_policy_tests | missing_jurisdiction_predicate | jurisdiction_scope | 120 | 85500.0 |
| field_policy_tests | missing_object_scope_predicate | object_scope | 120 | 85500.0 |
| full_without_object_scope | missing_jurisdiction_predicate | jurisdiction_scope | 120 | 85500.0 |

## Scale Sweep

| Multiplier | Method | Policies | Variants | Executions | Seconds | Recall |
|---:|---|---:|---:|---:|---:|---:|
| 1 | role_matrix | 12 | 120 | 1080 | 0.0062 | 0.2222 |
| 1 | policy_aware_full | 12 | 120 | 1080 | 0.0062 | 1.0 |
| 2 | role_matrix | 24 | 240 | 2160 | 0.0124 | 0.2222 |
| 2 | policy_aware_full | 24 | 240 | 2160 | 0.0124 | 1.0 |
| 4 | role_matrix | 48 | 480 | 4320 | 0.025 | 0.2222 |
| 4 | policy_aware_full | 48 | 480 | 4320 | 0.025 | 1.0 |
| 8 | role_matrix | 96 | 960 | 8640 | 0.0543 | 0.2222 |
| 8 | policy_aware_full | 96 | 960 | 8640 | 0.0543 | 1.0 |
| 10 | role_matrix | 120 | 1200 | 10800 | 0.0618 | 0.2222 |
| 10 | policy_aware_full | 120 | 1200 | 10800 | 0.0618 | 1.0 |

## Paired Delta Against Role-Matrix Baseline

| Metric | Mean delta | 95% CI | Proposed better | Tie | Baseline better |
|---|---:|---:|---:|---:|---:|
| detected | 0.7778 | [0.7537, 0.8019] | 840 | 240 | 0 |
| risk_flagged | 0.0509 | [0.0483, 0.0535] | 840 | 240 | 0 |

## Interpretation Notes

- Structural schema validation is expected to miss policy bugs because the mutated APIs can still return schema-valid payloads.
- Role-only tests catch missing authentication and coarse over-permission, but they miss object-level, field-level, purpose, and audit failures.
- The full policy-aware test suite detects all injected policy-bug families in this deterministic benchmark; ablation rows quantify which policy dimensions carry that coverage.
