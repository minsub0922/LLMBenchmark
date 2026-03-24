#!/usr/bin/env python3
"""
Legacy-compatible remote review runner.

This script keeps the older interface style:
- required: --input_file, --output_dir
- optional: --endpoint, --model, --workers, --timeout, --max_retries, --retry_sleep

It additionally supports recursive self-feed quality improvement while preserving
original meaning and labels.
"""

import argparse
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config import ReviewConfig, DEFAULT_BATCH_SIZE, DEFAULT_MAX_PASSES, DEFAULT_MODE
from pipeline_runner import NotificationReviewPipeline


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--endpoint", type=str, default=os.environ.get("ENDPOINT"))
    parser.add_argument("--model", type=str, default=os.environ.get("MODEL"))
    parser.add_argument("--workers", type=int, default=int(os.environ.get("WORKERS", "4")))
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("TIMEOUT", "180")))
    parser.add_argument("--max_retries", type=int, default=int(os.environ.get("MAX_RETRIES", "3")))
    parser.add_argument("--retry_sleep", type=float, default=float(os.environ.get("RETRY_SLEEP", "2.0")))

    # backward-compatible shell wrappers already pass BATCH_SIZE via env,
    # so keep that behavior without forcing a new CLI arg.
    parser.add_argument("--batch_size", type=int, default=int(os.environ.get("BATCH_SIZE", str(DEFAULT_BATCH_SIZE))))
    parser.add_argument("--max_passes", type=int, default=int(os.environ.get("MAX_PASSES", str(DEFAULT_MAX_PASSES))))
    parser.add_argument("--mode", type=str, default=os.environ.get("MODE", DEFAULT_MODE))
    parser.add_argument("--dry_run", action="store_true", default=os.environ.get("DRY_RUN", "0") == "1")
    parser.add_argument("--checks", type=str, default=os.environ.get("CHECKS", "grammar,title_summary,field_consistency"))
    return parser.parse_args()


def main():
    args = parse_args()

    cfg = ReviewConfig(
        input_file=args.input_file,
        output_dir=args.output_dir,
        endpoint=args.endpoint,
        model=args.model,
        batch_size=args.batch_size,
        workers=args.workers,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_sleep=args.retry_sleep,
        max_passes=args.max_passes,
        mode=args.mode,
        dry_run=args.dry_run,
        checks=[x.strip() for x in args.checks.split(",") if x.strip()],
    )

    print(f"[INFO] Loaded config: endpoint={cfg.endpoint}")
    print(f"[INFO] model={cfg.model}")
    print(f"[INFO] workers={cfg.workers}")
    print(f"[INFO] batch_size={cfg.batch_size}")
    print(f"[INFO] checks={cfg.checks}")
    print(f"[INFO] max_passes={cfg.max_passes}")
    print(f"[INFO] mode={cfg.mode}")

    runner = NotificationReviewPipeline(cfg)
    outputs = runner.run()

    print("[INFO] Done")
    for k, v in outputs.items():
        print(f"[INFO] {k}={v}")


if __name__ == "__main__":
    main()
