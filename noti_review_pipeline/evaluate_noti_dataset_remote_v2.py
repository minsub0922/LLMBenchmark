#!/usr/bin/env python3
"""
Modular remote evaluator for notification dataset quality.

This runner keeps the interface conceptually aligned with the earlier remote
script, while exposing more evaluation features:
- row-by-row scoring
- criterion subset selection
- low-score filtering
- before/after comparison support through a companion script
- JSONL/CSV/XLSX exports
"""

import argparse
import os
import sys
from typing import List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config import DEFAULT_ENDPOINT, DEFAULT_MODEL
from eval_config import normalize_criteria
from eval_reporter import build_eval_summary, filter_rows_by_threshold
from eval_runner import run_parallel_evaluation
from io_utils import dump_csv, dump_jsonl, dump_xlsx, ensure_dir, load_jsonl
from remote_client import RemoteInferenceClient



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
    parser.add_argument("--criteria", type=str, default=os.environ.get("EVAL_CRITERIA", ""))
    parser.add_argument("--low_score_threshold", type=float, default=float(os.environ.get("LOW_SCORE_THRESHOLD", "0")))
    return parser.parse_args()



def main():
    args = parse_args()
    ensure_dir(args.output_dir)

    criteria: List[str] = normalize_criteria(args.criteria)

    client = RemoteInferenceClient(
        endpoint=args.endpoint,
        model=args.model,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_sleep=args.retry_sleep,
    )

    records = load_jsonl(args.input_file)
    base_name = os.path.splitext(os.path.basename(args.input_file))[0]
    criteria_tag = "all" if not args.criteria else args.criteria.replace(",", "-")

    rows = run_parallel_evaluation(
        records=records,
        client=client,
        workers=args.workers,
        criteria=criteria,
    )
    summary_rows = build_eval_summary(rows)

    prefix = f"{base_name}.evaluation.{criteria_tag}"
    detail_jsonl = os.path.join(args.output_dir, f"{prefix}.detail.jsonl")
    detail_csv = os.path.join(args.output_dir, f"{prefix}.detail.csv")
    detail_xlsx = os.path.join(args.output_dir, f"{prefix}.detail.xlsx")

    dump_jsonl(detail_jsonl, rows)
    dump_csv(detail_csv, rows)
    dump_xlsx(detail_xlsx, {
        "summary": summary_rows,
        "details": rows,
    })

    if args.low_score_threshold > 0:
        low_rows = filter_rows_by_threshold(rows, threshold=args.low_score_threshold)
        low_jsonl = os.path.join(args.output_dir, f"{prefix}.low_le_{args.low_score_threshold}.jsonl")
        low_csv = os.path.join(args.output_dir, f"{prefix}.low_le_{args.low_score_threshold}.csv")
        low_xlsx = os.path.join(args.output_dir, f"{prefix}.low_le_{args.low_score_threshold}.xlsx")
        dump_jsonl(low_jsonl, low_rows)
        dump_csv(low_csv, low_rows)
        dump_xlsx(low_xlsx, {
            "low_score_rows": low_rows,
        })
        print(f"[INFO] low_jsonl={low_jsonl}")
        print(f"[INFO] low_csv={low_csv}")
        print(f"[INFO] low_xlsx={low_xlsx}")

    print(f"[INFO] input_file={args.input_file}")
    print(f"[INFO] output_dir={args.output_dir}")
    print(f"[INFO] criteria={criteria}")
    print(f"[INFO] detail_jsonl={detail_jsonl}")
    print(f"[INFO] detail_csv={detail_csv}")
    print(f"[INFO] detail_xlsx={detail_xlsx}")


if __name__ == "__main__":
    main()
