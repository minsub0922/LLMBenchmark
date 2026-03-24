# Notification Review Pipeline

This folder contains a modular pipeline for reviewing and lightly improving reservation-notification datasets through a remote inference endpoint.

## Goals
- keep the original meaning and labels intact
- improve only data quality issues such as grammar, spacing, malformed title style, and small expression inconsistencies
- run recursively with self-feed when needed
- export JSONL, CSV, and XLSX outputs
- keep the legacy shell interface working

## Main entrypoints
- `review_noti_pde_th_dataset_remote.py`: legacy-compatible single-command runner
- `review_noti_pde_th_dataset_remote.sh`: shell wrapper using env vars
- `run_noti_review_pipeline.sh`: full or partial pipeline runner

## Legacy-compatible usage
```bash
INPUT_FILE=/path/to/reservation_th.jsonl \
RESULT_DIR=results/thai_remote_review2 \
MODEL=qwen3.5-397b-a17b-fp8 \
BATCH_SIZE=20 \
WORKERS=4 \
ENDPOINT=https://inference-aistudio-data-synthesis.shuttle-stg.sr-cloud.com/generate \
python noti_review_pipeline/review_noti_pde_th_dataset_remote.py \
  --input_file "$INPUT_FILE" \
  --output_dir "$RESULT_DIR" \
  --model "$MODEL" \
  --workers "$WORKERS"
```

or

```bash
INPUT_FILE=/path/to/reservation_th.jsonl \
RESULT_DIR=results/thai_remote_review2 \
MODEL=qwen3.5-397b-a17b-fp8 \
BATCH_SIZE=20 \
WORKERS=4 \
ENDPOINT=https://inference-aistudio-data-synthesis.shuttle-stg.sr-cloud.com/generate \
bash noti_review_pipeline/review_noti_pde_th_dataset_remote.sh
```

## Optional controls
- `CHECKS`: comma-separated checks. default: `grammar,title_summary,field_consistency`
- `MAX_PASSES`: recursive improvement passes. default: `2`
- `MODE`: `full`, `review_only`, `apply_only`, `export_only`. default: `full`
- `DRY_RUN`: `1` to review without applying suggestions

## Output naming
Output filenames automatically include the active config, for example:

`reservation_th__grammar-title_summary-field_consistency__p2__full.improved.jsonl`

This makes large experiment sets easier to manage.
