# Main Experiment Report

## Campaign

- Policies/endpoints: 120
- Variants: 1200
- Injected buggy variants: 1080
- Test cases: 1080
- Test-level findings: 79200
- Elapsed seconds: 0.3994

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
| audit_contract_tests | missing_auth | authentication | 0.0 | 228000.0 |
| deprecated_inventory_tests | missing_auth | authentication | 0.0 | 228000.0 |
| field_policy_tests | missing_auth | authentication | 0.0 | 228000.0 |
| schema_validation | missing_auth | authentication | 0.0 | 228000.0 |
| audit_contract_tests | overbroad_role | function_authorization | 0.0 | 136800.0 |
| auth_required | overbroad_role | function_authorization | 0.0 | 136800.0 |
| deprecated_inventory_tests | overbroad_role | function_authorization | 0.0 | 136800.0 |
| field_policy_tests | overbroad_role | function_authorization | 0.0 | 136800.0 |
| schema_validation | overbroad_role | function_authorization | 0.0 | 136800.0 |
| audit_contract_tests | deprecated_exposed | endpoint_inventory | 0.0 | 102600.0 |
| auth_required | deprecated_exposed | endpoint_inventory | 0.0 | 102600.0 |
| field_policy_tests | deprecated_exposed | endpoint_inventory | 0.0 | 102600.0 |
| object_policy_tests | deprecated_exposed | endpoint_inventory | 0.0 | 102600.0 |
| role_matrix | deprecated_exposed | endpoint_inventory | 0.0 | 102600.0 |
| schema_validation | deprecated_exposed | endpoint_inventory | 0.0 | 102600.0 |
| audit_contract_tests | jurisdiction_bypass | jurisdiction_scope | 0.0 | 85500.0 |
| audit_contract_tests | missing_object_check | object_scope | 0.0 | 85500.0 |
| auth_required | jurisdiction_bypass | jurisdiction_scope | 0.0 | 85500.0 |

## Exposure Summary

| Bug type | Dimension | Events | Extra fields | Sensitive extra fields | Event risk |
|---|---|---:|---:|---:|---:|
| missing_auth | authentication | 120 | 960 | 760 | 6630.0 |
| overbroad_role | function_authorization | 120 | 960 | 760 | 6630.0 |
| jurisdiction_bypass | jurisdiction_scope | 120 | 670 | 530 | 5530.0 |
| missing_object_check | object_scope | 120 | 670 | 530 | 5530.0 |
| purpose_bypass | purpose_scope | 120 | 670 | 530 | 5530.0 |
| missing_field_filter | field_minimization | 580 | 1430 | 1110 | 5370.0 |
| missing_audit_log | audit_obligation | 1080 | 0 | 0 | 3240.0 |
| deprecated_exposed | endpoint_inventory | 120 | 290 | 230 | 1580.0 |
| aggregation_leak | aggregation_boundary | 120 | 290 | 230 | 1100.0 |

## Ablation Loss

| Ablation | Dimension | Bug type | Lost detections | Risk lost |
|---|---|---|---:|---:|
| full_without_object_scope | jurisdiction_scope | jurisdiction_bypass | 120 | 85500.0 |
| full_without_object_scope | object_scope | missing_object_check | 120 | 85500.0 |
| full_without_field_scope | field_minimization | missing_field_filter | 120 | 74000.0 |
| full_without_field_scope | aggregation_boundary | aggregation_leak | 120 | 59200.0 |
| full_without_purpose | purpose_scope | purpose_bypass | 120 | 45600.0 |
| full_without_audit | audit_obligation | missing_audit_log | 120 | 34200.0 |

## Main Interpretation

- Schema validation remains blind to policy bugs when responses are structurally valid.
- Role matrices detect coarse function authorization but miss object, jurisdiction, purpose, field, audit, and inventory obligations.
- Object-policy and field-policy tests each detect their own family but leave large missed-risk regions.
- The proposed suite is strongest because it combines decision, response-minimization, side-effect, and inventory oracles.
