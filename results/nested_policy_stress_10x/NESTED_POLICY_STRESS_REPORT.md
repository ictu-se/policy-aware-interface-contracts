# Nested Policy Stress Experiment

## Design

- Scenarios: 280
- Methods: 11
- Method-scenario judgments: 3080
- Stress dimensions: purpose-conditioned fields, jurisdiction-conditioned fields, consent-gated fields, aggregation thresholds, emergency audit escalation, and compound interactions.

## Method Summary

| Method | Precision | Recall | F1 | Risk-weighted recall |
|---|---:|---:|---:|---:|
| dependent_policy_full | 1.0 | 1.0 | 1.0 | 1.0 |
| dependent_without_enhanced_audit | 1.0 | 0.8333 | 0.9091 | 0.9 |
| dependent_without_threshold | 1.0 | 0.8333 | 0.9091 | 0.875 |
| dependent_without_consent | 1.0 | 0.8333 | 0.9091 | 0.85 |
| dependent_without_purpose_field | 1.0 | 0.8333 | 0.9091 | 0.825 |
| audit_contract_tests | 0.0 | 0.0 | 0.0 | 0.0 |
| basic_policy_aware_full | 0.0 | 0.0 | 0.0 | 0.0 |
| field_policy_tests | 0.0 | 0.0 | 0.0 | 0.0 |
| object_policy_tests | 0.0 | 0.0 | 0.0 | 0.0 |
| role_matrix | 0.0 | 0.0 | 0.0 | 0.0 |
| schema_validation | 0.0 | 0.0 | 0.0 | 0.0 |

## Recall by Dependent Failure

| Method | Failure | Recall | Risk-weighted recall |
|---|---|---:|---:|
| basic_policy_aware_full | aggregation_threshold_leak | 0.0 | 0.0 |
| basic_policy_aware_full | compound_scope_field | 0.0 | 0.0 |
| basic_policy_aware_full | consent_gated_field | 0.0 | 0.0 |
| basic_policy_aware_full | emergency_audit_downgrade | 0.0 | 0.0 |
| basic_policy_aware_full | jurisdiction_conditioned_field | 0.0 | 0.0 |
| basic_policy_aware_full | purpose_conditioned_field | 0.0 | 0.0 |
| dependent_policy_full | aggregation_threshold_leak | 1.0 | 1.0 |
| dependent_policy_full | compound_scope_field | 1.0 | 1.0 |
| dependent_policy_full | consent_gated_field | 1.0 | 1.0 |
| dependent_policy_full | emergency_audit_downgrade | 1.0 | 1.0 |
| dependent_policy_full | jurisdiction_conditioned_field | 1.0 | 1.0 |
| dependent_policy_full | purpose_conditioned_field | 1.0 | 1.0 |
| dependent_without_consent | aggregation_threshold_leak | 1.0 | 1.0 |
| dependent_without_consent | compound_scope_field | 1.0 | 1.0 |
| dependent_without_consent | consent_gated_field | 0.0 | 0.0 |
| dependent_without_consent | emergency_audit_downgrade | 1.0 | 1.0 |
| dependent_without_consent | jurisdiction_conditioned_field | 1.0 | 1.0 |
| dependent_without_consent | purpose_conditioned_field | 1.0 | 1.0 |
| dependent_without_enhanced_audit | aggregation_threshold_leak | 1.0 | 1.0 |
| dependent_without_enhanced_audit | compound_scope_field | 1.0 | 1.0 |
| dependent_without_enhanced_audit | consent_gated_field | 1.0 | 1.0 |
| dependent_without_enhanced_audit | emergency_audit_downgrade | 0.0 | 0.0 |
| dependent_without_enhanced_audit | jurisdiction_conditioned_field | 1.0 | 1.0 |
| dependent_without_enhanced_audit | purpose_conditioned_field | 1.0 | 1.0 |
| dependent_without_purpose_field | aggregation_threshold_leak | 1.0 | 1.0 |
| dependent_without_purpose_field | compound_scope_field | 1.0 | 1.0 |
| dependent_without_purpose_field | consent_gated_field | 1.0 | 1.0 |
| dependent_without_purpose_field | emergency_audit_downgrade | 1.0 | 1.0 |
| dependent_without_purpose_field | jurisdiction_conditioned_field | 1.0 | 1.0 |
| dependent_without_purpose_field | purpose_conditioned_field | 0.0 | 0.0 |
| dependent_without_threshold | aggregation_threshold_leak | 0.0 | 0.0 |
| dependent_without_threshold | compound_scope_field | 1.0 | 1.0 |
| dependent_without_threshold | consent_gated_field | 1.0 | 1.0 |
| dependent_without_threshold | emergency_audit_downgrade | 1.0 | 1.0 |
| dependent_without_threshold | jurisdiction_conditioned_field | 1.0 | 1.0 |
| dependent_without_threshold | purpose_conditioned_field | 1.0 | 1.0 |
| field_policy_tests | aggregation_threshold_leak | 0.0 | 0.0 |
| field_policy_tests | compound_scope_field | 0.0 | 0.0 |
| field_policy_tests | consent_gated_field | 0.0 | 0.0 |
| field_policy_tests | emergency_audit_downgrade | 0.0 | 0.0 |
| field_policy_tests | jurisdiction_conditioned_field | 0.0 | 0.0 |
| field_policy_tests | purpose_conditioned_field | 0.0 | 0.0 |
| object_policy_tests | aggregation_threshold_leak | 0.0 | 0.0 |
| object_policy_tests | compound_scope_field | 0.0 | 0.0 |
| object_policy_tests | consent_gated_field | 0.0 | 0.0 |
| object_policy_tests | emergency_audit_downgrade | 0.0 | 0.0 |
| object_policy_tests | jurisdiction_conditioned_field | 0.0 | 0.0 |
| object_policy_tests | purpose_conditioned_field | 0.0 | 0.0 |

## Interpretation

- The basic full suite is complete for the original independent-dimension benchmark but blind to policy dependencies not represented in the contract.
- Dependent policy clauses recover the missed cases by adding explicit interaction oracles rather than by increasing random test volume.
- The stress test therefore narrows the perfect-score claim: full recall holds for represented obligations, while nested production policies require explicit dependent clauses.
