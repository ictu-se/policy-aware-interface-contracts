# Sensitivity and Benign-Variation Stress Report

## Campaign

- Policies/endpoints: 120
- Variants: 1200
- Buggy variants: 1080
- Benign stress cases: 4440

## Risk-Weight Sensitivity

| Risk scheme | Full suite recall | Role matrix recall | Schema recall | Full suite rank |
|---|---:|---:|---:|---:|
| equal | 1.0 | 0.2222 | 0.0 | 1 |
| severity_only | 1.0 | 0.2368 | 0.0 | 1 |
| current | 1.0 | 0.4285 | 0.0 | 1 |
| privacy_heavy | 1.0 | 0.3657 | 0.0 | 1 |
| audit_inventory_heavy | 1.0 | 0.3851 | 0.0 | 1 |

## Benign-Variation False-Positive Stress

| Case type | N | False positives | False-positive rate |
|---|---:|---:|---:|
| allowed_empty_body | 600 | 0 | 0.0 |
| allowed_full_shuffled | 600 | 0 | 0.0 |
| allowed_full_sorted | 600 | 0 | 0.0 |
| allowed_minimal_subset | 600 | 0 | 0.0 |
| allowed_with_extra_audit_metadata | 600 | 0 | 0.0 |
| denied_audit_logged | 480 | 0 | 0.0 |
| denied_empty_body | 480 | 0 | 0.0 |
| deprecated_endpoint_unavailable | 480 | 0 | 0.0 |
| overall | 4440 | 0 | 0.0 |

## Interpretation

- The full policy-aware suite remains top-ranked under all tested risk-weight schemes.
- The benign stress cases produce zero false positives, indicating that the oracle accepts policy-compliant implementation variation such as response-field subsets and different field orderings.
