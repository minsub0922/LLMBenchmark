# Remote HF v3 Guide

This document explains how to use `review_noti_pde_th_dataset_remote_hf_v3.py` in detail.

The v3 runner is the recommended choice when you need:

- recursive self-feed review
- human-feedback-aware title fixing
- conservative grammar / formatting cleanup
- full per-row change history
- Excel outputs that can be filtered by change type, changed fields, and reasons

---

## What v3 does

The runner reviews each JSONL row and tries to improve only **low-risk data-quality issues**.

It is designed to preserve:

- reservation status
- dates and times
- reservation numbers
- hotel / property names
- room / item names
- addresses
- core semantics

It is designed to improve only:

- wrong grammar
- awkward phrasing
- weak summary-like title text
- title that does not cover the body content
- spacing / punctuation / malformed line breaks

It should **not rewrite the sample into a different style** or invent missing facts.

---

## Main file

- `noti_review_pipeline/review_noti_pde_th_dataset_remote_hf_v3.py`

---

## Interface compatibility

The interface intentionally follows the earlier remote runner style.

Required arguments:

- `--input_file`
- `--output_dir`

Environment-variable-driven execution is also supported.

Example:

```bash
INPUT_FILE=/group-volume/manner.choi/projects/noti_gauss3.8/datasets/250305/v0.0.16_pass/reservation/reservation_th.jsonl \
RESULT_DIR=results/thai_hf_v3 \
MODEL=qwen3.5-397b-a17b-fp8 \
WORKERS=4 \
CHECKS=grammar,title_summary,field_consistency \
FEEDBACK_PROFILE=title_grammar_coverage_v1 \
python noti_review_pipeline/review_noti_pde_th_dataset_remote_hf_v3.py \
  --input_file "$INPUT_FILE" \
  --output_dir "$RESULT_DIR"
```

---

## Parameters

### Core parameters

- `--input_file`: input JSONL file
- `--output_dir`: output directory
- `--endpoint`: remote endpoint
- `--model`: model name
- `--workers`: number of parallel workers
- `--timeout`: request timeout
- `--max_retries`: retry count
- `--retry_sleep`: retry sleep seconds
- `--batch_size`: compatibility/logging value

### Review-control parameters

- `--checks`: comma-separated review checks
- `--max_passes`: recursive pass count
- `--mode`: review/apply mode
- `--dry_run`: review only, do not apply changes
- `--feedback_profile`: human-feedback profile

---

## Checks

Typical checks:

- `grammar`
- `title_summary`
- `field_consistency`
- `format_consistency`

Recommended default:

```bash
CHECKS=grammar,title_summary,field_consistency
```

---

## Feedback profiles

### 1. `none`
Use when you only want generic low-risk cleanup.

### 2. `title_grammar_v1`
Use when:

- Thai grammar is weak
- title wording is awkward
- title contains generic booking confirmation phrasing
- duplicated booking prefixes appear

### 3. `title_content_coverage_v1`
Use when:

- title is too generic
- title does not expose the main reserved entity
- body contains a clear venue / service / property name

Example target direction:

- `การจอง` -> `การจอง Fujiflim-XSpace-TH`

### 4. `title_grammar_coverage_v1`
Use when both of these are needed together:

- grammar cleanup
- title-content coverage improvement

This is usually the best default for your task.

---

## Case-by-case usage

### Case 1. Generic title only
Problem:

- title is only `การจอง`
- body contains the actual reserved entity

Recommended:

```bash
INPUT_FILE=/path/to/input.jsonl \
RESULT_DIR=results/case_generic_title \
MODEL=qwen3.5-397b-a17b-fp8 \
WORKERS=4 \
CHECKS=title_summary \
FEEDBACK_PROFILE=title_content_coverage_v1 \
python noti_review_pipeline/review_noti_pde_th_dataset_remote_hf_v3.py \
  --input_file "$INPUT_FILE" \
  --output_dir "$RESULT_DIR"
```

Expected direction:

- `การจอง` -> `การจอง {main_entity}`

---

### Case 2. Generic title + grammar issue together
Problem:

- title is weak summary label
- body Thai grammar is awkward
- human feedback wants `การจอง {hotel_name} {room_type}`-style title

Recommended:

```bash
INPUT_FILE=/path/to/input.jsonl \
RESULT_DIR=results/case_title_grammar \
MODEL=qwen3.5-397b-a17b-fp8 \
WORKERS=4 \
CHECKS=grammar,title_summary,field_consistency \
FEEDBACK_PROFILE=title_grammar_coverage_v1 \
python noti_review_pipeline/review_noti_pde_th_dataset_remote_hf_v3.py \
  --input_file "$INPUT_FILE" \
  --output_dir "$RESULT_DIR"
```

---

### Case 3. Only formatting cleanup
Problem:

- repeated blank lines
- spacing issue
- malformed punctuation
- title is already good enough

Recommended:

```bash
INPUT_FILE=/path/to/input.jsonl \
RESULT_DIR=results/case_format_only \
MODEL=qwen3.5-397b-a17b-fp8 \
WORKERS=4 \
CHECKS=format_consistency \
FEEDBACK_PROFILE=none \
python noti_review_pipeline/review_noti_pde_th_dataset_remote_hf_v3.py \
  --input_file "$INPUT_FILE" \
  --output_dir "$RESULT_DIR"
```

---

### Case 4. Conservative audit without mutating data
Problem:

- you want row scores and reasons first
- you do not want to change the train data yet

Recommended:

```bash
INPUT_FILE=/path/to/input.jsonl \
RESULT_DIR=results/case_audit_only \
MODEL=qwen3.5-397b-a17b-fp8 \
WORKERS=4 \
MODE=review_only \
DRY_RUN=1 \
FEEDBACK_PROFILE=title_grammar_coverage_v1 \
python noti_review_pipeline/review_noti_pde_th_dataset_remote_hf_v3.py \
  --input_file "$INPUT_FILE" \
  --output_dir "$RESULT_DIR" \
  --dry_run
```

---

### Case 5. Recursive self-feed improvement
Problem:

- one pass is not enough
- there are recurring low-quality title/grammar issues across the dataset

Recommended:

```bash
INPUT_FILE=/path/to/input.jsonl \
RESULT_DIR=results/case_recursive \
MODEL=qwen3.5-397b-a17b-fp8 \
WORKERS=4 \
MAX_PASSES=3 \
CHECKS=grammar,title_summary,field_consistency \
FEEDBACK_PROFILE=title_grammar_coverage_v1 \
python noti_review_pipeline/review_noti_pde_th_dataset_remote_hf_v3.py \
  --input_file "$INPUT_FILE" \
  --output_dir "$RESULT_DIR"
```

Guideline:

- `MAX_PASSES=1`: fast review
- `MAX_PASSES=2`: recommended default
- `MAX_PASSES=3`: use only if you still observe repeated low-quality patterns

---

## Output files

The output file name automatically contains the active config.

Example:

```text
reservation_th__grammar-title_summary-field_consistency__p2__full__fb_title_grammar_coverage_v1.improved.jsonl
reservation_th__grammar-title_summary-field_consistency__p2__full__fb_title_grammar_coverage_v1.history.csv
reservation_th__grammar-title_summary-field_consistency__p2__full__fb_title_grammar_coverage_v1.history.xlsx
```

This helps when you run many experiments.

---

## History outputs

### 1. `*.improved.jsonl`
The final improved dataset.

### 2. `*.history.csv`
Machine-readable detailed history.

### 3. `*.history.xlsx`
Human-auditable workbook with filters.

---

## Excel workbook structure

### Sheet: `history_all`
Contains all reviewed rows.

### Sheet: `changed_only`
Contains only rows where actual changes were applied.

### Sheet: `change_summary`
Contains aggregated counts by change type and change tags.

### Sheet: `final_records`
Contains final exported records.

All sheets include:

- frozen header row
- auto filter
- auto-sized columns

---

## History columns

The detailed history includes:

- `row_id`
- `pass_idx`
- `feedback_profile`
- `decision`
- `changed`
- `change_type`
- `change_tags`
- `changed_fields`
- `reason`
- `title_before`
- `title_after`
- `title_changed`
- `body_changed`
- `grammar_score`
- `naturalness_score`
- `title_quality_score`
- `format_consistency_score`
- `original_text`
- `final_text`

---

## Change types

Designed for Excel filtering:

- `no_change`
- `title_only`
- `grammar_only`
- `format_only`
- `body_only`
- `title_and_body`
- `other_change`

## Change tags

Examples:

- `title_changed`
- `body_changed`
- `grammar_fix`
- `format_fix`
- `title_quality_fix`

These tags can overlap, so a row can be discoverable through multiple perspectives.

---

## What the history is useful for

You asked for history to be important. The v3 history is meant to answer all of these:

- which row changed?
- on which pass?
- did only the title change, or the body too?
- what was the old title?
- what is the new title?
- what reasons did the model mention?
- what type of change was it?
- what rows were not changed?
- which rows were changed only because of title coverage?
- which rows were changed mainly because of grammar?

---

## Practical recommendation for your task

For your reservation-notification dataset, the best default starting setup is usually:

```bash
INPUT_FILE=/path/to/input.jsonl \
RESULT_DIR=results/default_run \
MODEL=qwen3.5-397b-a17b-fp8 \
WORKERS=4 \
CHECKS=grammar,title_summary,field_consistency \
FEEDBACK_PROFILE=title_grammar_coverage_v1 \
MAX_PASSES=2 \
python noti_review_pipeline/review_noti_pde_th_dataset_remote_hf_v3.py \
  --input_file "$INPUT_FILE" \
  --output_dir "$RESULT_DIR"
```

Use this when you want:

- improved train data
- title correction
- grammar cleanup
- row-level Excel audit trail

---

## Notes

- `batch_size` is kept mainly for interface compatibility and run logging.
- The remote endpoint is request-based; actual quality depends on the endpoint model behavior.
- The pipeline is designed for **light corrective improvement**, not semantic rewriting.
- If you discover more recurring human-feedback patterns later, extend the feedback-profile dictionary instead of adding one-off hardcoded exceptions.
