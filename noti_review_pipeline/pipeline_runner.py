import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

from config import ReviewConfig
from io_utils import dump_csv, dump_jsonl, dump_xlsx, ensure_dir, load_jsonl
from remote_client import RemoteInferenceClient
from review_logic import build_review_prompt, decide_and_apply, parse_json_response


class NotificationReviewPipeline:
    """
    Modular pipeline for remote review and light improvement.

    Process stages:
    1. load input JSONL
    2. review each row with the remote model
    3. optionally apply safe improvements
    4. recursively self-feed for multiple passes
    5. export JSONL / CSV / XLSX summaries

    The pipeline intentionally focuses on data quality and readability.
    It must not rewrite labels or alter factual content.
    """

    def __init__(self, cfg: ReviewConfig):
        self.cfg = cfg
        self.client = RemoteInferenceClient(
            endpoint=cfg.endpoint,
            model=cfg.model,
            timeout=cfg.timeout,
            max_retries=cfg.max_retries,
            retry_sleep=cfg.retry_sleep,
        )
        ensure_dir(cfg.output_dir)

    def _review_one(self, idx: int, record: Dict[str, Any]) -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
        prompt = build_review_prompt(record.get("text", ""), self.cfg.checks)
        raw = self.client.generate(prompt)
        review = parse_json_response(raw)
        updated, row = decide_and_apply(record, review, self.cfg.dry_run)
        row["row_id"] = idx
        return idx, updated, row

    def review_pass(self, records: List[Dict[str, Any]], pass_idx: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        next_records: List[Dict[str, Any]] = [None] * len(records)  # type: ignore
        rows: List[Dict[str, Any]] = [None] * len(records)  # type: ignore

        with ThreadPoolExecutor(max_workers=self.cfg.workers) as ex:
            futures = [ex.submit(self._review_one, idx, rec) for idx, rec in enumerate(records)]
            for fut in as_completed(futures):
                idx, updated, row = fut.result()
                row["pass_idx"] = pass_idx
                next_records[idx] = updated
                rows[idx] = row

        return next_records, rows

    def run(self) -> Dict[str, str]:
        records = load_jsonl(self.cfg.input_file)
        base_name = os.path.splitext(os.path.basename(self.cfg.input_file))[0]
        slug = self.cfg.run_slug()

        all_rows: List[Dict[str, Any]] = []
        current_records = records

        if self.cfg.mode in {"full", "review_only", "apply_only"}:
            for pass_idx in range(1, self.cfg.max_passes + 1):
                current_records, rows = self.review_pass(current_records, pass_idx)
                all_rows.extend(rows)
                if self.cfg.mode == "review_only":
                    break

        improved_jsonl = os.path.join(self.cfg.output_dir, f"{base_name}__{slug}.improved.jsonl")
        review_csv = os.path.join(self.cfg.output_dir, f"{base_name}__{slug}.review.csv")
        review_xlsx = os.path.join(self.cfg.output_dir, f"{base_name}__{slug}.review.xlsx")

        dump_jsonl(improved_jsonl, current_records)
        dump_csv(review_csv, all_rows)
        dump_xlsx(
            review_xlsx,
            {
                "review_rows": all_rows,
                "final_records": current_records,
            },
        )

        return {
            "improved_jsonl": improved_jsonl,
            "review_csv": review_csv,
            "review_xlsx": review_xlsx,
        }
