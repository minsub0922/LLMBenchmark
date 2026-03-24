from typing import Any, Dict, List



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



def filter_rows_by_threshold(rows: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
    filtered = []
    for row in rows:
        score = row.get("overall_score", "")
        try:
            if float(score) <= threshold:
                filtered.append(row)
        except Exception:
            continue
    return filtered
