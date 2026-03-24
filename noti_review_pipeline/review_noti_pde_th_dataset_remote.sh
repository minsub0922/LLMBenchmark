#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"

INPUT_FILE="${INPUT_FILE:-}"
RESULT_DIR="${RESULT_DIR:-}"
ENDPOINT="${ENDPOINT:-https://inference-aistudio-data-synthesis.shuttle-stg.sr-cloud.com/generate}"
MODEL="${MODEL:-qwen3.5-397b-a17b-fp8}"
WORKERS="${WORKERS:-4}"
BATCH_SIZE="${BATCH_SIZE:-20}"
TIMEOUT="${TIMEOUT:-180}"
MAX_RETRIES="${MAX_RETRIES:-3}"
RETRY_SLEEP="${RETRY_SLEEP:-2.0}"
MAX_PASSES="${MAX_PASSES:-2}"
MODE="${MODE:-full}"
DRY_RUN="${DRY_RUN:-0}"
CHECKS="${CHECKS:-grammar,title_summary,field_consistency}"

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
echo "[INFO] BATCH_SIZE=$BATCH_SIZE"
echo "[INFO] CHECKS=$CHECKS"
echo "[INFO] MAX_PASSES=$MAX_PASSES"
echo "[INFO] MODE=$MODE"

"$PYTHON_BIN" "$SCRIPT_DIR/review_noti_pde_th_dataset_remote.py" \
  --input_file "$INPUT_FILE" \
  --output_dir "$RESULT_DIR" \
  --endpoint "$ENDPOINT" \
  --model "$MODEL" \
  --workers "$WORKERS" \
  --timeout "$TIMEOUT" \
  --max_retries "$MAX_RETRIES" \
  --retry_sleep "$RETRY_SLEEP" \
  --batch_size "$BATCH_SIZE" \
  --max_passes "$MAX_PASSES" \
  --mode "$MODE" \
  --checks "$CHECKS" \
  ${DRY_RUN:+--dry_run}
