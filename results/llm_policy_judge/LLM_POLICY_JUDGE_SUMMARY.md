# LLM Policy-Judge Summary

## Overall

| Model | N | Parse | Decision acc. | Strict acc. | Precision | Recall | F1 | Risk recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen2.5-coder:14b | 120 | 1.0 | 0.8333 | 0.4833 | 0.9074 | 0.9074 | 0.9074 | 0.875 |
| qwen2.5-coder:32b | 120 | 1.0 | 0.8 | 0.4667 | 0.9375 | 0.8333 | 0.8824 | 0.8151 |
| qwen2.5-coder:7b | 120 | 1.0 | 0.7 | 0.2917 | 0.9 | 0.75 | 0.8182 | 0.8116 |
| gemma3:4b | 120 | 1.0 | 0.9 | 0.2833 | 0.9 | 1.0 | 0.9474 | 1.0 |
| qwen2.5-coder:3b | 120 | 1.0 | 0.4167 | 0.2 | 0.88 | 0.4074 | 0.557 | 0.4793 |
| phi3:mini | 120 | 1.0 | 0.9 | 0.1917 | 0.9 | 1.0 | 0.9474 | 1.0 |
| deepseek-coder:6.7b | 120 | 1.0 | 0.8083 | 0.1833 | 0.8972 | 0.8889 | 0.893 | 0.9334 |
| qwen2.5:3b | 120 | 1.0 | 0.325 | 0.125 | 0.8649 | 0.2963 | 0.4414 | 0.3352 |
| llama3.2:3b | 120 | 1.0 | 0.7917 | 0.1167 | 0.9029 | 0.8611 | 0.8815 | 0.9272 |
| qwen2.5-coder:1.5b | 120 | 1.0 | 0.9 | 0.1 | 0.9 | 1.0 | 0.9474 | 1.0 |
| qwen3:4b | 120 | 0.0 | 0.1 | 0.1 | 0.0 | 0.0 | 0.0 | 0.0 |

Main comparison uses the 120 case IDs present for every scored model.

## Lowest Dimension Groups

| Model | Group | N | Strict acc. | Dimension acc. | Recall |
|---|---|---:|---:|---:|---:|
| deepseek-coder:6.7b | aggregation_boundary | 12 | 0.0 | 0.0 | 1.0 |
| deepseek-coder:6.7b | audit_obligation | 12 | 0.0 | 0.0 | 0.4167 |
| deepseek-coder:6.7b | endpoint_inventory | 12 | 0.0 | 0.0 | 1.0 |
| deepseek-coder:6.7b | field_minimization | 12 | 0.0 | 0.0 | 1.0 |
| deepseek-coder:6.7b | jurisdiction_scope | 12 | 0.0 | 0.0 | 0.8333 |
| deepseek-coder:6.7b | purpose_scope | 12 | 0.0 | 0.0 | 0.9167 |
| gemma3:4b | aggregation_boundary | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b | endpoint_inventory | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b | jurisdiction_scope | 12 | 0.0 | 0.0 | 1.0 |
| gemma3:4b | purpose_scope | 12 | 0.0 | 0.0 | 1.0 |
| llama3.2:3b | aggregation_boundary | 12 | 0.0 | 0.0 | 0.75 |
| llama3.2:3b | audit_obligation | 12 | 0.0 | 0.0 | 0.9167 |
| llama3.2:3b | authentication | 12 | 0.0 | 0.0 | 1.0 |
| llama3.2:3b | endpoint_inventory | 12 | 0.0 | 0.0 | 0.5 |
| llama3.2:3b | field_minimization | 12 | 0.0 | 0.0 | 0.8333 |
| llama3.2:3b | jurisdiction_scope | 12 | 0.0 | 0.0 | 1.0 |
| llama3.2:3b | object_scope | 12 | 0.0 | 0.0 | 1.0 |
| llama3.2:3b | purpose_scope | 12 | 0.0 | 0.0 | 0.75 |
| phi3:mini | aggregation_boundary | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini | endpoint_inventory | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini | field_minimization | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini | jurisdiction_scope | 12 | 0.0 | 0.0 | 1.0 |
| phi3:mini | object_scope | 12 | 0.0 | 0.0 | 1.0 |
| qwen2.5-coder:1.5b | aggregation_boundary | 12 | 0.0 | 0.0 | 1.0 |
| qwen2.5-coder:1.5b | audit_obligation | 12 | 0.0 | 0.0 | 1.0 |
| qwen2.5-coder:1.5b | authentication | 12 | 0.0 | 0.0 | 1.0 |
| qwen2.5-coder:1.5b | endpoint_inventory | 12 | 0.0 | 0.0 | 1.0 |
| qwen2.5-coder:1.5b | field_minimization | 12 | 0.0 | 0.0 | 1.0 |
| qwen2.5-coder:1.5b | jurisdiction_scope | 12 | 0.0 | 0.0 | 1.0 |
| qwen2.5-coder:1.5b | object_scope | 12 | 0.0 | 0.0 | 1.0 |
