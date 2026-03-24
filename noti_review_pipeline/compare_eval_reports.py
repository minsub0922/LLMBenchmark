#!/usr/bin/env python3
"""
Compare two evaluation detail reports.

Use this after evaluating a dataset before/after cleanup.
The script compares row-by-row scores and exports summary + joined details.
"""

import argparse
import os
import sys
from typing import Dict, List

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from io_utils import dump_csv, dump_jsonl, dump_xlsx, ensure_dir, load_jsonl


KEYS_TO_COMPARE = [
    "overall_score",
    "grammar_score",
    "naturalness_score",
    "title_quality_score",
    "format_consistency_score",
    "semantic_preservation_risk_score",
]



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before_file", type=str, required=True)
    parser.add_argument("--after_file", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    return parser.parse_args()



def to_float(v):
    try:
        return float(v)
    except Exception:
        return None



def main():
    args = parse_args()
    ensure_dir(args.output_dir)

    before_rows = load_jsonl(args.before_file)
    after_rows = load_jsonl(args.after_file)
    before_map: Dict[int, Dict] = {int(r["row_id"]): r for r in before_rows}
    after_map: Dict[int, Dict] = {int(r["row_id"]): r for r in after_rows}

    row_ids = sorted(set(before_map.keys()) & set(after_map.keys()))
    joined: List[Dict] = []

    for row_id in row_ids:
        b = before_map[row_id]
        a = after_map[row_id]
        row = {"row_id": row_id}
        for key in KEYS_TO_COMPARE:
            bv = b.get(key, "")
            av = a.get(key, "")
            row[f"before__{key}"] = bv
            row[f"after__{key}"] = av
            bf = to_float(bv)
            af = to_float(av)
            row[f"delta__{key}"] = round(af - bf, 4) if bf is not None and af is not None else ""
        row["before__summary"] = b.get("summary", "")
        row["after__summary"] = a.get("summary", "")
        row["text"] = a.get("text", b.get("text", ""))
        joined.append(row)

    def avg_delta(name: str) -> float:
        vals = [r[f"delta__{name}"] for r in joined if isinstance(r.get(f"delta__{name}"), (int, float))]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    summary = [{
        "num_compared_rows": len(joined),
        **{f"avg_delta__{k}": avg_delta(k) for k in KEYS_TO_COMPARE},
    }]

    prefix = os.path.join(args.output_dir, "evaluation_comparison")
    dump_jsonl(prefix + ".jsonl", joined)
    dump_csv(prefix + ".csv", joined)
    dump_xlsx(prefix + ".xlsx", {"summary": summary, "details": joined})

    print(f"[INFO] before_file={args.before_file}")
    print(f"[INFO] after_file={args.after_file}")
    print(f"[INFO] output_dir={args.output_dir}")
    print(f"[INFO] comparison_jsonl={prefix + '.jsonl'}")
    print(f"[INFO] comparison_csv={prefix + '.csv'}")
    print(f"[INFO] comparison_xlsx={prefix + '.xlsx'}")


if __name__ == "__main__":
    main()
