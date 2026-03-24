import json
import re
from typing import Any, Dict, Tuple


def extract_text_field(record: Dict[str, Any]) -> str:
    return str(record.get('text', ''))


def replace_text_field(record: Dict[str, Any], new_text: str) -> Dict[str, Any]:
    out = dict(record)
    out['text'] = new_text
    return out


def parse_json_response(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r'\{.*\}', raw, flags=re.DOTALL)
    if not m:
        raise ValueError('No JSON object found in response')
    return json.loads(m.group(0))


def decide_and_apply(record: Dict[str, Any], review: Dict[str, Any], dry_run: bool) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    original_text = extract_text_field(record)
    decision = str(review.get('decision', 'keep')).strip().lower()
    improved_text = str(review.get('improved_text', original_text))
    issues = review.get('issues', [])
    change_types = review.get('change_type', [])
    scores = review.get('quality_scores', {})
    reason = review.get('reason', '')

    changed = (
        decision == 'improve'
        and improved_text.strip()
        and improved_text.strip() != original_text.strip()
        and not dry_run
    )
    updated_record = replace_text_field(record, improved_text) if changed else dict(record)

    if isinstance(issues, list):
        issue_text = ' | '.join(str(x) for x in issues)
    else:
        issue_text = str(issues)

    if isinstance(change_types, list):
        change_type_text = ' | '.join(str(x) for x in change_types)
    else:
        change_type_text = str(change_types)

    row = {
        'decision': decision,
        'changed': changed,
        'change_type': change_type_text,
        'issues': issue_text,
        'reason': str(reason),
        'grammar_score': scores.get('grammar', ''),
        'naturalness_score': scores.get('naturalness', ''),
        'title_quality_score': scores.get('title_quality', ''),
        'format_consistency_score': scores.get('format_consistency', ''),
        'original_text': original_text,
        'final_text': extract_text_field(updated_record),
    }
    return updated_record, row
