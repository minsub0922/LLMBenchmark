import json
import re
from typing import Any, Dict, List, Tuple


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


def extract_text_field(record: Dict[str, Any]) -> str:
    return str(record.get("text", ""))


def replace_text_field(record: Dict[str, Any], new_text: str) -> Dict[str, Any]:
    out = dict(record)
    out["text"] = new_text
    return out


def build_review_prompt(text: str, checks: List[str]) -> str:
    return (
        SYSTEM_RULES
        + "\n\n"
        + f"Active checks: {', '.join(checks)}\n\n"
        + "Review this sample and improve it only if needed.\n\n"
        + "[SAMPLE]\n"
        + text
    )


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


def decide_and_apply(record: Dict[str, Any], review: Dict[str, Any], dry_run: bool) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    original_text = extract_text_field(record)
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
        "final_text": extract_text_field(updated_record),
    }
    return updated_record, row
