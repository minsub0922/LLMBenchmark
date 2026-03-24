#!/usr/bin/env python3
"""
Human-feedback-aware remote review runner v2.

This variant keeps the same interface style as the earlier HF runner, while
adding a clearer title-content-coverage profile for cases such as:
- title is too generic: "การจอง"
- title does not expose the reserved entity shown in the body
- desired output should be like: "การจอง Fujiflim-XSpace-TH"
"""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config import DEFAULT_BATCH_SIZE, DEFAULT_ENDPOINT, DEFAULT_MAX_PASSES, DEFAULT_MODEL, DEFAULT_MODE
from io_utils import dump_csv, dump_jsonl, dump_xlsx, ensure_dir, load_jsonl
from remote_client import RemoteInferenceClient


HUMAN_FEEDBACK_PROFILES: Dict[str, str] = {
    "none": "",
    "title_grammar_v1": (
        "Apply these human-feedback-based preferences only when clearly supported by the sample text:\n"
        "1. If the title is a weak synthetic label, duplicated brand phrase, or generic confirmation phrase, rewrite the title to a more useful reservation-style title.\n"
        "2. Prefer the Thai title pattern 'การจอง {hotel_name} {room_type}' when both hotel/property name and room type are explicitly present in the sample.\n"
        "3. Remove duplicated booking-brand prefixes or generic phrases like 'การยืนยันการจอง' when a clearer reservation title can be formed.\n"
        "4. Improve wrong grammar, awkward Thai phrasing, spacing, and punctuation in the raw notification text.\n"
        "5. Do not invent hotel name, room type, date, or other facts that are not explicitly present.\n"
        "6. Keep semantic meaning, reservation status, ids, and all factual content unchanged.\n"
    ),
    "title_content_coverage_v1": (
        "Apply these title-content-coverage preferences only when clearly supported by the sample text:\n"
        "1. If the title is too generic, such as only 'การจอง', 'การจองของคุณได้รับการยืนยัน', or similar, rewrite it so the main reserved entity is visible in the title.\n"
        "2. The rewritten title should cover the core content of the reservation, especially the venue / property / service name explicitly shown in the sample.\n"
        "3. Prefer the compact Thai pattern 'การจอง {main_entity}' when the sample mainly provides one clear reserved entity, for example an event space, venue, hotel, or service name.\n"
        "4. If both a clear property/service name and a clear room/item name are explicitly present, you may prefer 'การจอง {property_name} {room_or_item_name}' only when it remains natural and not overly long.\n"
        "5. Do not leave the title as a bare generic reservation label if the body clearly identifies what was reserved.\n"
        "6. Do not invent missing entities. Keep all factual content and meaning unchanged.\n"
    ),
    "title_grammar_coverage_v1": (
        "Combine grammar cleanup and title-content coverage rules when clearly supported by the sample text:\n"
        "1. Improve wrong grammar, awkward Thai phrasing, spacing, punctuation, and malformed line breaks in the raw notification text.\n"
        "2. If the title is generic or summary-like and does not cover the actual reservation content, rewrite it to expose the main reserved entity.\n"
        "3. Prefer 'การจอง {main_entity}' when the sample provides one clear venue/property/service name.\n"
        "4. Prefer 'การจอง {hotel_name} {room_type}' when both hotel/property and room/item are explicitly present and the result is natural.\n"
        "5. Remove duplicated brand prefixes or generic confirmation wording when a clearer reservation title can be formed.\n"
        "6. Do not invent facts. Keep reservation status, ids, dates, times, entities, and semantics unchanged.\n"
    ),
}


SYSTEM_RULES = """
You are a careful dataset quality reviewer for reservation notification extraction data.

Your goal is NOT to change the meaning, facts, labels, entity values, dates, times, addresses, reservation ids, or cancellation/confirmation status.
You may ONLY improve data quality in limited ways:
1. fix obvious grammar or spacing issues in the raw notification text
2. fix broken punctuation or malformed line breaks
3. improve title text when it is a low-quality synthetic summary label rather than a natural title, but preserve meaning
4. normalize tiny expression issues without changing semantics
5. never invent missing facts
6. never rewrite the sample into a different style if the original is already acceptable

Return strict JSON:
{
  "decision": "keep" | "improve",
  "issues": ["..."],
  "improved_text": "...",
  "quality_scores": {
    "grammar": 1-5,
    "naturalness": 1-5,
    "title_quality": 1-5,
    "format_consistency": 1-5
  }
}
""".strip()



def build_review_prompt(text: str, checks: List[str], feedback_profile: str = "none") -> str:
    feedback_instruction = HUMAN_FEEDBACK_PROFILES.get(feedback_profile, "")
    prompt = SYSTEM_RULES + "\n\n" + f"Active checks: {', '.join(checks)}\n"
    if feedback_instruction:
        prompt += "\nHuman feedback preferences:\n" + feedback_instruction + "\n"
    prompt += "\nReview this sample and improve it only if needed.\n\n[SAMPLE]\n" + text
    return prompt



def parse_json_response(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in response")
    return json.loads(m.group(0))



def replace_text_field(record: Dict[str, Any], new_text: str) -> Dict[str, Any]:
    out = dict(record)
    out["text"] = new_text
    return out



def decide_and_apply(record: Dict[str, Any], review: Dict[str, Any], dry_run: bool) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    original_text = str(record.get("text", ""))
    decision = str(review.get("decision", "keep")).strip().lower()
    improved_text = str(review.get("improved_text", original_text))
    issues = review.get("issues", [])
    scores = review.get("quality_scores", {})

    changed = decision == "improve" and improved_text.strip() and improved_text.strip() != original_text.strip() and not dry_run
    updated_record = replace_text_field(record, improved_text) if changed else dict(record)

    row = {
        "decision": decision,
        "changed": changed,
        "issues": " | ".join(issues) if isinstance(issues, list) else str(issues),
        "grammar_score": scores.get("grammar", ""),
        "naturalness_score": scores.get("naturalness", ""),
        "title_quality_score": scores.get("title_quality", ""),
        "format_consistency_score": scores.get("format_consistency", ""),
        "original_text": original_text,
        "final_text": str(updated_record.get("text", "")),
    }
    return updated_record, row



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
    prompt = build_review_prompt(str(record.get("text", "")), checks, feedback_profile=feedback_profile)
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
