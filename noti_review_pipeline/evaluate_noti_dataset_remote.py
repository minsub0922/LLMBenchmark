#!/usr/bin/env python3
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config import DEFAULT_ENDPOINT, DEFAULT_MODEL
from eval_logic import build_eval_prompt, build_eval_summary, flatten_eval_result, parse_eval_response
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
    return parser.parse_args()


def evaluate_one(client: RemoteInferenceClient, row_id: int, record: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    text = str(record.get("text", ""))
    prompt = build_eval_prompt(text)
    raw = client.generate(prompt)
    parsed = parse_eval_response(raw)
    row = flatten_eval_result(row_id=row_id, text=text, result=parsed)
    return row_id, row


def main():
    args = parse_args()
    ensure_dir(args.output_dir)

    client = RemoteInferenceClient(
        endpoint=args.endpoint,
        model=args.model,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_sleep=args.retry_sleep,
    )

    records = load_jsonl(args.input_file)
    base_name = os.path.splitext(os.path.basename(args.input_file))[0]
    rows: List[Dict[str, Any]] = [None] * len(records)  # type: ignore

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(evaluate_one, client, idx, rec) for idx, rec in enumerate(records)]
        for fut in as_completed(futures):
            idx, row = fut.result()
            rows[idx] = row

    summary_rows = build_eval_summary(rows)

    detail_jsonl = os.path.join(args.output_dir, f"{base_name}.evaluation.detail.jsonl")
    detail_csv = os.path.join(args.output_dir, f"{base_name}.evaluation.detail.csv")
    detail_xlsx = os.path.join(args.output_dir, f"{base_name}.evaluation.detail.xlsx")

    dump_jsonl(detail_jsonl, rows)
    dump_csv(detail_csv, rows)
    dump_xlsx(detail_xlsx, {
        "summary": summary_rows,
        "details": rows,
    })

    print(f"[INFO] input_file={args.input_file}")
    print(f"[INFO] output_dir={args.output_dir}")
    print(f"[INFO] detail_jsonl={detail_jsonl}")
    print(f"[INFO] detail_csv={detail_csv}")
    print(f"[INFO] detail_xlsx={detail_xlsx}")


if __name__ == "__main__":
    main()
