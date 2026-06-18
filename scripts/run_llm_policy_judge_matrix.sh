#!/usr/bin/env bash
set -euo pipefail

MODELS=(
  "qwen2.5-coder:1.5b"
  "qwen2.5-coder:3b"
  "qwen2.5-coder:7b"
  "qwen2.5-coder:14b"
  "qwen2.5-coder:32b"
  "deepseek-coder:6.7b"
  "gemma3:4b"
  "qwen2.5:3b"
  "qwen3:4b"
  "llama3.2:3b"
  "phi3:mini"
)

MAX_ITEMS="${MAX_ITEMS:-360}"
TIMEOUT="${TIMEOUT:-240}"

for model in "${MODELS[@]}"; do
  echo "=== ${model} ==="
  python3 scripts/run_llm_policy_judge.py \
    --model "${model}" \
    --max-items "${MAX_ITEMS}" \
    --balanced \
    --resume \
    --timeout "${TIMEOUT}"
done

python3 scripts/score_llm_policy_judge.py
