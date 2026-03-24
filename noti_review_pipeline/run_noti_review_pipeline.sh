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
MAX_PASSES="${MAX_PASSES:-2}"
CHECKS="${CHECKS:-grammar,title_summary,field_consistency}"
MODE="${MODE:-full}"
DRY_RUN="${DRY_RUN:-0}"

if [[ -z "$INPUT_FILE" || -z "$RESULT_DIR" ]]; then
  echo "[ERROR] INPUT_FILE and RESULT_DIR are required"
  exit 1
fi

ARGS=(
  --input_file "$INPUT_FILE"
  --output_dir "$RESULT_DIR"
  --endpoint "$ENDPOINT"
  --model "$MODEL"
  --workers "$WORKERS"
  --batch_size "$BATCH_SIZE"
  --max_passes "$MAX_PASSES"
  --mode "$MODE"
  --checks "$CHECKS"
)

if [[ "$DRY_RUN" == "1" ]]; then
  ARGS+=(--dry_run)
fi

"$PYTHON_BIN" "$SCRIPT_DIR/review_noti_pde_th_dataset_remote.py" "${ARGS[@]}"
