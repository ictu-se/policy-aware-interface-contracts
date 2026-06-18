# LLM Policy-Judge Summary

## Overall

| Model | N | Parse | Decision acc. | Strict acc. | Precision | Recall | F1 | Risk recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen2.5-coder:14b|conservative | 120 | 1.0 | 0.8167 | 0.4917 | 0.9216 | 0.8704 | 0.8952 | 0.8186 |
| qwen2.5-coder:14b|checklist | 120 | 1.0 | 0.8333 | 0.4833 | 0.9074 | 0.9074 | 0.9074 | 0.875 |
| qwen2.5-coder:14b|minimal | 120 | 1.0 | 0.8417 | 0.4167 | 0.9159 | 0.9074 | 0.9116 | 0.8685 |
| gemma3:4b|checklist | 120 | 1.0 | 0.9 | 0.3167 | 0.9 | 1.0 | 0.9474 | 1.0 |
| phi3:mini|minimal | 120 | 1.0 | 0.5833 | 0.2333 | 0.8816 | 0.6204 | 0.7283 | 0.7684 |
| phi3:mini|conservative | 120 | 1.0 | 0.9 | 0.225 | 0.9 | 1.0 | 0.9474 | 1.0 |
| phi3:mini|checklist | 120 | 1.0 | 0.9 | 0.1917 | 0.9 | 1.0 | 0.9474 | 1.0 |
| gemma3:4b|conservative | 120 | 1.0 | 0.9 | 0.1833 | 0.9 | 1.0 | 0.9474 | 1.0 |
| gemma3:4b|minimal | 120 | 1.0 | 0.35 | 0.0917 | 0.875 | 0.3241 | 0.473 | 0.2962 |

Main comparison uses the 120 case IDs present for every scored model.

## Lowest Dimension Groups

| Model | Group | N | Strict acc. | Dimension acc. | Recall |
|---|---|---:|---:|---:|---:|
| gemma3:4b|checklist | aggregation_boundary | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|checklist | endpoint_inventory | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|checklist | jurisdiction_scope | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|checklist | purpose_scope | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|conservative | aggregation_boundary | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|conservative | audit_obligation | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|conservative | authentication | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|conservative | endpoint_inventory | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|conservative | jurisdiction_scope | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|conservative | object_scope | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|conservative | purpose_scope | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|minimal | aggregation_boundary | 12 | 0.0 | 0.0 | 0.25 |
| gemma3:4b|minimal | audit_obligation | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b|minimal | authentication | 12 | 0.0 | 0.0 | 0.4167 |
| gemma3:4b|minimal | endpoint_inventory | 12 | 0.0 | 0.0 | 0.0 |
| gemma3:4b|minimal | function_authorization | 12 | 0.0 | 0.0 | 0.1667 |
| gemma3:4b|minimal | jurisdiction_scope | 12 | 0.0 | 0.0 | 0.25 |
| gemma3:4b|minimal | purpose_scope | 12 | 0.0 | 0.0 | 0.4167 |
| phi3:mini|checklist | aggregation_boundary | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini|checklist | endpoint_inventory | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini|checklist | field_minimization | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini|checklist | jurisdiction_scope | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini|checklist | object_scope | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini|conservative | aggregation_boundary | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini|conservative | endpoint_inventory | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini|conservative | field_minimization | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini|conservative | jurisdiction_scope | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini|conservative | object_scope | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini|minimal | aggregation_boundary | 12 | 0.0 | 0.0 | 0.1667 |
| phi3:mini|minimal | audit_obligation | 12 | 0.0 | 0.0 | 1.0 |
