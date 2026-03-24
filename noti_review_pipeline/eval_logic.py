import json
import re
from typing import Any, Dict, List


EVAL_SYSTEM_RULES = """
You are a strict evaluator for reservation-notification dataset quality.

Evaluate each sample on the following criteria only:
1. grammar_quality: grammar, spacing, punctuation, awkward wording
2. naturalness_quality: whether the notification sounds like a realistic user-facing message
3. title_quality: whether title-like content is natural rather than a synthetic summary label
4. format_consistency: structure, line breaks, delimiter consistency, field formatting consistency
5. semantic_preservation_risk: risk that the sample contains confusing wording that may distort original meaning

Important rules:
- Do not change the sample.
- Do not judge business correctness unless it is directly visible from the text itself.
- Focus on quality of the dataset text.
- Be specific and evidence-based.

Return strict JSON:
{
  "overall_score": 1-5,
  "criteria": {
    "grammar_quality": {"score": 1-5, "reason": "..."},
    "naturalness_quality": {"score": 1-5, "reason": "..."},
    "title_quality": {"score": 1-5, "reason": "..."},
    "format_consistency": {"score": 1-5, "reason": "..."},
    "semantic_preservation_risk": {"score": 1-5, "reason": "..."}
  },
  "major_issues": ["..."],
  "improvement_suggestions": ["..."],
  "summary": "..."
}
""".strip()


def build_eval_prompt(text: str) -> str:
    return (
        EVAL_SYSTEM_RULES
        + "\n\n"
        + "Evaluate this sample in detail.\n\n"
        + "[SAMPLE]\n"
        + text
    )


def parse_eval_response(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        pass
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in evaluation response")
    return json.loads(m.group(0))


def flatten_eval_result(row_id: int, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
    criteria = result.get("criteria", {}) or {}

    def c(name: str, key: str):
        item = criteria.get(name, {}) or {}
        return item.get(key, "")

    return {
        "row_id": row_id,
        "overall_score": result.get("overall_score", ""),
        "grammar_score": c("grammar_quality", "score"),
        "grammar_reason": c("grammar_quality", "reason"),
        "naturalness_score": c("naturalness_quality", "score"),
        "naturalness_reason": c("naturalness_quality", "reason"),
        "title_quality_score": c("title_quality", "score"),
        "title_quality_reason": c("title_quality", "reason"),
        "format_consistency_score": c("format_consistency", "score"),
        "format_consistency_reason": c("format_consistency", "reason"),
        "semantic_preservation_risk_score": c("semantic_preservation_risk", "score"),
        "semantic_preservation_risk_reason": c("semantic_preservation_risk", "reason"),
        "major_issues": " | ".join(result.get("major_issues", []) or []),
        "improvement_suggestions": " | ".join(result.get("improvement_suggestions", []) or []),
        "summary": result.get("summary", ""),
        "text": text,
    }


def build_eval_summary(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return [{"message": "no rows"}]

    def avg(key: str) -> float:
        vals = []
        for r in rows:
            v = r.get(key, "")
            if isinstance(v, (int, float)):
                vals.append(float(v))
            elif isinstance(v, str) and v.strip().isdigit():
                vals.append(float(v))
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    return [{
        "num_rows": len(rows),
        "overall_score_avg": avg("overall_score"),
        "grammar_score_avg": avg("grammar_score"),
        "naturalness_score_avg": avg("naturalness_score"),
        "title_quality_score_avg": avg("title_quality_score"),
        "format_consistency_score_avg": avg("format_consistency_score"),
        "semantic_preservation_risk_score_avg": avg("semantic_preservation_risk_score"),
    }]
