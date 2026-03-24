# commands

This directory documents runnable command examples for the notification review pipeline.

## Typical full run
```bash
INPUT_FILE=/path/to/reservation_th.jsonl \
RESULT_DIR=results/thai_remote_review \
MODEL=qwen3.5-397b-a17b-fp8 \
BATCH_SIZE=20 \
WORKERS=4 \
CHECKS=grammar,title_summary,field_consistency \
FEEDBACK_PROFILE=title_grammar_coverage_v1 \
bash review_noti_pde_th_dataset_remote.sh
```

## Review only
```bash
python noti_review_pipeline/cli/remote_review_cli.py \
  --input_file /path/to/reservation_th.jsonl \
  --output_dir results/review_only \
  --mode review_only \
  --checks grammar,title_summary
```

## Dry run
```bash
python noti_review_pipeline/cli/remote_review_cli.py \
  --input_file /path/to/reservation_th.jsonl \
  --output_dir results/dry_run \
  --dry_run \
  --feedback_profile title_grammar_v1
```
