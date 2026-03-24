#!/usr/bin/env python3
"""
Human-feedback-aware remote review runner.

This keeps the existing interface style while adding optional parameters to
inject curated human feedback rules into the dataset-improvement prompt.
It does not replace the existing runner.
"""

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config import DEFAULT_BATCH_SIZE, DEFAULT_ENDPOINT, DEFAULT_MAX_PASSES, DEFAULT_MODEL, DEFAULT_MODE
from io_utils import dump_csv, dump_jsonl, dump_xlsx, ensure_dir, load_jsonl
from remote_client import RemoteInferenceClient
from review_logic_hf import build_review_prompt, decide_and_apply, parse_json_response



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--endpoint", type=str, default=os.environ.get("ENDPOINT", DEFAULT_ENDPOINT))
    parser.add_argument("--model", type=str, default=os.environ.get("MODEL", DEFAULT_MODEL))
    parser.add_argument("--workers", type=int, default=int(os.environ.get("WORKERS", "4")))
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("TIMEOUT", "180")))
    parser.add_argument("--max_retries", type=int, default=int(os.environ.get("MAX_RETRIES", "3")))
    parser.add_argument("--retry_sleep", type=float, default=float(os.environ.get("RETRY_SLEEP", "2.0")))
    parser.add_argument("--batch_size", type=int, default=int(os.environ.get("BATCH_SIZE", str(DEFAULT_BATCH_SIZE))))
    parser.add_argument("--max_passes", type=int, default=int(os.environ.get("MAX_PASSES", str(DEFAULT_MAX_PASSES))))
    parser.add_argument("--mode", type=str, default=os.environ.get("MODE", DEFAULT_MODE))
    parser.add_argument("--dry_run", action="store_true", default=os.environ.get("DRY_RUN", "0") == "1")
    parser.add_argument("--checks", type=str, default=os.environ.get("CHECKS", "grammar,title_summary,field_consistency"))
    parser.add_argument("--feedback_profile", type=str, default=os.environ.get("FEEDBACK_PROFILE", "none"))
    return parser.parse_args()



def run_slug(checks: List[str], max_passes: int, mode: str, dry_run: bool, feedback_profile: str) -> str:
    checks_slug = "-".join(checks) if checks else "none"
    fb_slug = f"__fb_{feedback_profile}" if feedback_profile and feedback_profile != "none" else ""
    return f"{checks_slug}__p{max_passes}__{mode}{'__dry' if dry_run else ''}{fb_slug}"



def review_one(
    client: RemoteInferenceClient,
    idx: int,
    record: Dict[str, Any],
    checks: List[str],
    dry_run: bool,
    feedback_profile: str,
) -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
    prompt = build_review_prompt(record.get("text", ""), checks, feedback_profile=feedback_profile)
    raw = client.generate(prompt)
    review = parse_json_response(raw)
    updated, row = decide_and_apply(record, review, dry_run)
    row["row_id"] = idx
    row["feedback_profile"] = feedback_profile
    return idx, updated, row



def review_pass(
    client: RemoteInferenceClient,
    records: List[Dict[str, Any]],
    pass_idx: int,
    workers: int,
    checks: List[str],
    dry_run: bool,
    feedback_profile: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    next_records: List[Dict[str, Any]] = [None] * len(records)  # type: ignore
    rows: List[Dict[str, Any]] = [None] * len(records)  # type: ignore

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [
            ex.submit(review_one, client, idx, rec, checks, dry_run, feedback_profile)
            for idx, rec in enumerate(records)
        ]
        for fut in as_completed(futures):
            idx, updated, row = fut.result()
            row["pass_idx"] = pass_idx
            next_records[idx] = updated
            rows[idx] = row

    return next_records, rows



def main():
    args = parse_args()
    ensure_dir(args.output_dir)

    checks = [x.strip() for x in args.checks.split(",") if x.strip()]
    client = RemoteInferenceClient(
        endpoint=args.endpoint,
        model=args.model,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_sleep=args.retry_sleep,
    )

    print(f"[INFO] endpoint={args.endpoint}")
    print(f"[INFO] model={args.model}")
    print(f"[INFO] workers={args.workers}")
    print(f"[INFO] batch_size={args.batch_size}")
    print(f"[INFO] checks={checks}")
    print(f"[INFO] max_passes={args.max_passes}")
    print(f"[INFO] mode={args.mode}")
    print(f"[INFO] feedback_profile={args.feedback_profile}")

    records = load_jsonl(args.input_file)
    base_name = os.path.splitext(os.path.basename(args.input_file))[0]
    slug = run_slug(checks, args.max_passes, args.mode, args.dry_run, args.feedback_profile)

    all_rows: List[Dict[str, Any]] = []
    current_records = records

    if args.mode in {"full", "review_only", "apply_only"}:
        for pass_idx in range(1, args.max_passes + 1):
            current_records, rows = review_pass(
                client=client,
                records=current_records,
                pass_idx=pass_idx,
                workers=args.workers,
                checks=checks,
                dry_run=args.dry_run,
                feedback_profile=args.feedback_profile,
            )
            all_rows.extend(rows)
            if args.mode == "review_only":
                break

    improved_jsonl = os.path.join(args.output_dir, f"{base_name}__{slug}.improved.jsonl")
    review_csv = os.path.join(args.output_dir, f"{base_name}__{slug}.review.csv")
    review_xlsx = os.path.join(args.output_dir, f"{base_name}__{slug}.review.xlsx")

    dump_jsonl(improved_jsonl, current_records)
    dump_csv(review_csv, all_rows)
    dump_xlsx(review_xlsx, {"review_rows": all_rows, "final_records": current_records})

    print("[INFO] Done")
    print(f"[INFO] improved_jsonl={improved_jsonl}")
    print(f"[INFO] review_csv={review_csv}")
    print(f"[INFO] review_xlsx={review_xlsx}")


if __name__ == "__main__":
    main()
