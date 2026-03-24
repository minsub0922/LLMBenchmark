import json
import os
from collections import Counter
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
        row["raw_response"] = raw
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

    def _build_summary(self, records_before: List[Dict[str, Any]], records_after: List[Dict[str, Any]], all_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_rows = len(records_before)
        changed_rows = 0
        raw_line_changed_rows = 0
        for before, after in zip(records_before, records_after):
            before_text = str(before.get("text", ""))
            after_text = str(after.get("text", ""))
            if before_text != after_text:
                changed_rows += 1
            if json.dumps(before, ensure_ascii=False) != json.dumps(after, ensure_ascii=False):
                raw_line_changed_rows += 1

        change_type_counts = Counter()
        parse_status_counts = Counter()
        issue_counts = Counter()
        applied_check_counts = Counter()
        pass_change_counts = Counter()

        for row in all_rows:
            parse_status_counts[str(row.get("parse_status", "unknown"))] += 1
            if row.get("changed"):
                ctype = str(row.get("change_type", "") or "unknown")
                change_type_counts[ctype] += 1
                pass_change_counts[str(row.get("pass_idx", "?"))] += 1
            issues = str(row.get("issues", "") or "")
            for part in [x.strip() for x in issues.split("|") if x.strip()]:
                issue_counts[part] += 1
            checks = str(row.get("applied_checks", "") or "")
            for part in [x.strip() for x in checks.split("|") if x.strip()]:
                applied_check_counts[part] += 1

        return {
            "input_file": self.cfg.input_file,
            "output_dir": self.cfg.output_dir,
            "endpoint": self.cfg.endpoint,
            "model": self.cfg.model,
            "workers": self.cfg.workers,
            "batch_size": self.cfg.batch_size,
            "timeout": self.cfg.timeout,
            "max_retries": self.cfg.max_retries,
            "retry_sleep": self.cfg.retry_sleep,
            "max_passes": self.cfg.max_passes,
            "mode": self.cfg.mode,
            "dry_run": self.cfg.dry_run,
            "checks": self.cfg.checks,
            "checks_slug": self.cfg.checks_slug(),
            "run_slug": self.cfg.run_slug(),
            "total_rows": total_rows,
            "changed_rows": changed_rows,
            "unchanged_rows": total_rows - changed_rows,
            "changed_ratio": round(changed_rows / total_rows, 6) if total_rows else 0.0,
            "raw_line_changed_rows": raw_line_changed_rows,
            "raw_line_changed_ratio": round(raw_line_changed_rows / total_rows, 6) if total_rows else 0.0,
            "change_type_counts": dict(change_type_counts),
            "parse_status_counts": dict(parse_status_counts),
            "issue_counts": dict(issue_counts),
            "applied_check_counts": dict(applied_check_counts),
            "pass_change_counts": dict(pass_change_counts),
        }

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

        summary = self._build_summary(records, current_records, all_rows)

        improved_jsonl = os.path.join(self.cfg.output_dir, f"{base_name}__{slug}.improved.jsonl")
        review_csv = os.path.join(self.cfg.output_dir, f"{base_name}__{slug}.review.csv")
        review_xlsx = os.path.join(self.cfg.output_dir, f"{base_name}__{slug}.review.xlsx")
        summary_json = os.path.join(self.cfg.output_dir, f"{base_name}__{slug}.summary.json")
        debug_jsonl = os.path.join(self.cfg.output_dir, f"{base_name}__{slug}.debug.jsonl")

        dump_jsonl(improved_jsonl, current_records)
        dump_csv(review_csv, all_rows)
        dump_xlsx(
            review_xlsx,
            {
                "summary": [{"key": k, "value": json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v} for k, v in summary.items()],
                "review_rows": all_rows,
                "changed_only": [r for r in all_rows if r.get("changed")],
                "final_records": current_records,
            },
        )
        with open(summary_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        dump_jsonl(debug_jsonl, [{
            "row_id": r.get("row_id"),
            "pass_idx": r.get("pass_idx"),
            "decision": r.get("decision"),
            "changed": r.get("changed"),
            "parse_status": r.get("parse_status"),
            "issues": r.get("issues"),
            "change_type": r.get("change_type"),
            "change_reason": r.get("change_reason"),
            "applied_checks": r.get("applied_checks"),
            "raw_response": r.get("raw_response"),
        } for r in all_rows])

        return {
            "improved_jsonl": improved_jsonl,
            "review_csv": review_csv,
            "review_xlsx": review_xlsx,
            "summary_json": summary_json,
            "debug_jsonl": debug_jsonl,
        }
