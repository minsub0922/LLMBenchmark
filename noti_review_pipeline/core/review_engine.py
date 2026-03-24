import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

from config.settings import ReviewConfig
from io.artifacts import dump_csv, dump_jsonl, dump_xlsx, ensure_dir, load_jsonl
from clients.remote_inference import RemoteInferenceClient
from core.prompts import build_review_prompt
from core.logic import decide_and_apply, parse_json_response
from core.history import build_history_sheet


class NotificationReviewPipeline:
    """Multi-pass review engine for dataset quality improvement.

    Responsibilities:
    - load input JSONL
    - call the remote model row by row
    - keep or lightly improve each row
    - preserve meaning, labels, ids, dates, times, and addresses
    - export review artifacts with full history
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
        prompt = build_review_prompt(
            text=record.get('text', ''),
            checks=self.cfg.checks,
            feedback_profile=self.cfg.feedback_profile,
        )
        raw = self.client.generate(prompt)
        review = parse_json_response(raw)
        updated, row = decide_and_apply(record, review, self.cfg.dry_run)
        row['row_id'] = idx
        return idx, updated, row

    def review_pass(self, records: List[Dict[str, Any]], pass_idx: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        next_records: List[Dict[str, Any]] = [None] * len(records)  # type: ignore
        rows: List[Dict[str, Any]] = [None] * len(records)  # type: ignore

        with ThreadPoolExecutor(max_workers=self.cfg.workers) as ex:
            futures = [ex.submit(self._review_one, idx, rec) for idx, rec in enumerate(records)]
            for fut in as_completed(futures):
                idx, updated, row = fut.result()
                row['pass_idx'] = pass_idx
                next_records[idx] = updated
                rows[idx] = row

        return next_records, rows

    def run(self) -> Dict[str, str]:
        records = load_jsonl(self.cfg.input_file)
        base_name = os.path.splitext(os.path.basename(self.cfg.input_file))[0]
        slug = self.cfg.run_slug()

        all_rows: List[Dict[str, Any]] = []
        current_records = records

        if self.cfg.mode in {'full', 'review_only', 'apply_only'}:
            for pass_idx in range(1, self.cfg.max_passes + 1):
                current_records, rows = self.review_pass(current_records, pass_idx)
                all_rows.extend(rows)
                if self.cfg.mode == 'review_only':
                    break

        history_rows = build_history_sheet(all_rows) if self.cfg.save_history else []

        improved_jsonl = os.path.join(self.cfg.output_dir, f'{base_name}__{slug}.improved.jsonl')
        review_csv = os.path.join(self.cfg.output_dir, f'{base_name}__{slug}.review.csv')
        review_xlsx = os.path.join(self.cfg.output_dir, f'{base_name}__{slug}.review.xlsx')

        dump_jsonl(improved_jsonl, current_records)
        dump_csv(review_csv, all_rows)
        dump_xlsx(
            review_xlsx,
            {
                'review_rows': all_rows,
                'history': history_rows,
                'final_records': current_records,
            },
        )

        return {
            'improved_jsonl': improved_jsonl,
            'review_csv': review_csv,
            'review_xlsx': review_xlsx,
        }
