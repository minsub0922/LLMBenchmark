#!/usr/bin/env python3
"""
Evaluate only selected issue categories on the dataset.

This is useful when you want to focus on the exact weak points discussed in the
project, such as:
- grammar / expression issues
- title as summary-label style
- unnatural formatting
"""

import argparse
import os
import sys
from typing import Dict, List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config import DEFAULT_ENDPOINT, DEFAULT_MODEL
from io_utils import dump_csv, dump_jsonl, dump_xlsx, ensure_dir, load_jsonl
from remote_client import RemoteInferenceClient


ISSUE_PRESETS: Dict[str, List[str]] = {
    "grammar": ["grammar_quality"],
    "naturalness": ["naturalness_quality"],
    "title": ["title_quality"],
    "format": ["format_consistency"],
    "semantic": ["semantic_preservation_risk"],
    "core": ["grammar_quality", "naturalness_quality", "title_quality"],
    "all": [
        "grammar_quality",
        "naturalness_quality",
        "title_quality",
        "format_consistency",
        "semantic_preservation_risk",
    ],
}



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--issue_preset", type=str, default=os.environ.get("ISSUE_PRESET", "core"))
    parser.add_argument("--endpoint", type=str, default=os.environ.get("ENDPOINT", DEFAULT_ENDPOINT))
    parser.add_argument("--model", type=str, default=os.environ.get("MODEL", DEFAULT_MODEL))
    parser.add_argument("--workers", type=int, default=int(os.environ.get("WORKERS", "4")))
    parser.add_argument("--timeout", type=int, default=int(os.environ.get("TIMEOUT", "180")))
    parser.add_argument("--max_retries", type=int, default=int(os.environ.get("MAX_RETRIES", "3")))
    parser.add_argument("--retry_sleep", type=float, default=float(os.environ.get("RETRY_SLEEP", "2.0")))
    return parser.parse_args()



def build_prompt(text: str, criteria: List[str]) -> str:
    criteria_desc = {
        "grammar_quality": "grammar, punctuation, spacing, expression quality",
        "naturalness_quality": "how realistic and natural the notification sounds",
        "title_quality": "whether title-like wording is synthetic or summary-labeled",
        "format_consistency": "format structure and delimiter consistency",
        "semantic_preservation_risk": "risk of confusion or meaning distortion",
    }
    lines = [f"- {c}: {criteria_desc.get(c, c)}" for c in criteria]
    json_lines = [f'    "{c}": {{"score": 1-5, "reason": "..."}}' for c in criteria]
    return (
        "You are a strict evaluator for reservation-notification dataset quality.\n"
        "Focus only on the selected issues below.\n\n"
        "Selected criteria:\n"
        + "\n".join(lines)
        + "\n\n"
        + "Return strict JSON:\n"
        + "{\n"
        + '  "overall_score": 1-5,\n'
        + '  "criteria": {\n'
        + ",\n".join(json_lines)
        + "\n  },\n"
        + '  "major_issues": ["..."],\n'
        + '  "improvement_suggestions": ["..."],\n'
        + '  "summary": "..."\n'
        + "}\n\n"
        + "[SAMPLE]\n"
        + text
    )



def parse_json(raw: str):
    import json
    import re
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON found")
    return json.loads(m.group(0))



def main():
    args = parse_args()
    ensure_dir(args.output_dir)
    preset = args.issue_preset
    if preset not in ISSUE_PRESETS:
        raise ValueError(f"Unknown issue_preset: {preset}. Available: {sorted(ISSUE_PRESETS.keys())}")
    criteria = ISSUE_PRESETS[preset]

    client = RemoteInferenceClient(
        endpoint=args.endpoint,
        model=args.model,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_sleep=args.retry_sleep,
    )

    records = load_jsonl(args.input_file)
    rows = []
    for idx, rec in enumerate(records):
        text = str(rec.get("text", ""))
        result = parse_json(client.generate(build_prompt(text, criteria)))
        row = {
            "row_id": idx,
            "overall_score": result.get("overall_score", ""),
            "major_issues": " | ".join(result.get("major_issues", []) or []),
            "improvement_suggestions": " | ".join(result.get("improvement_suggestions", []) or []),
            "summary": result.get("summary", ""),
            "text": text,
        }
        for c in criteria:
            item = (result.get("criteria", {}) or {}).get(c, {}) or {}
            row[f"{c}__score"] = item.get("score", "")
            row[f"{c}__reason"] = item.get("reason", "")
        rows.append(row)

    base_name = os.path.splitext(os.path.basename(args.input_file))[0]
    prefix = os.path.join(args.output_dir, f"{base_name}.selected_eval.{preset}")
    dump_jsonl(prefix + ".jsonl", rows)
    dump_csv(prefix + ".csv", rows)
    dump_xlsx(prefix + ".xlsx", {"details": rows})

    print(f"[INFO] issue_preset={preset}")
    print(f"[INFO] criteria={criteria}")
    print(f"[INFO] jsonl={prefix + '.jsonl'}")
    print(f"[INFO] csv={prefix + '.csv'}")
    print(f"[INFO] xlsx={prefix + '.xlsx'}")


if __name__ == "__main__":
    main()
