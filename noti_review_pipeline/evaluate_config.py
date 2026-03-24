from typing import List


DEFAULT_EVAL_CRITERIA: List[str] = [
    "grammar_quality",
    "naturalness_quality",
    "title_quality",
    "format_consistency",
    "semantic_preservation_risk",
]


def normalize_criteria(criteria_text: str | None) -> List[str]:
    if not criteria_text:
        return list(DEFAULT_EVAL_CRITERIA)
    items = [x.strip() for x in criteria_text.split(",") if x.strip()]
    if not items:
        return list(DEFAULT_EVAL_CRITERIA)
    return items
