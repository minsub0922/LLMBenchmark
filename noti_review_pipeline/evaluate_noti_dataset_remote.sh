#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"

INPUT_FILE="${INPUT_FILE:-}"
RESULT_DIR="${RESULT_DIR:-}"
ENDPOINT="${ENDPOINT:-https://inference-aistudio-data-synthesis.shuttle-stg.sr-cloud.com/generate}"
MODEL="${MODEL:-qwen3.5-397b-a17b-fp8}"
WORKERS="${WORKERS:-4}"
TIMEOUT="${TIMEOUT:-180}"
MAX_RETRIES="${MAX_RETRIES:-3}"
RETRY_SLEEP="${RETRY_SLEEP:-2.0}"

if [[ -z "$INPUT_FILE" ]]; then
  echo "[ERROR] INPUT_FILE is required"
  exit 1
fi

if [[ -z "$RESULT_DIR" ]]; then
  echo "[ERROR] RESULT_DIR is required"
  exit 1
fi

echo "[INFO] INPUT_FILE=$INPUT_FILE"
echo "[INFO] RESULT_DIR=$RESULT_DIR"
echo "[INFO] ENDPOINT=$ENDPOINT"
echo "[INFO] MODEL=$MODEL"
echo "[INFO] WORKERS=$WORKERS"

"$PYTHON_BIN" "$SCRIPT_DIR/evaluate_noti_dataset_remote.py" \
  --input_file "$INPUT_FILE" \
  --output_dir "$RESULT_DIR" \
  --endpoint "$ENDPOINT" \
  --model "$MODEL" \
  --workers "$WORKERS" \
  --timeout "$TIMEOUT" \
  --max_retries "$MAX_RETRIES" \
  --retry_sleep "$RETRY_SLEEP"
