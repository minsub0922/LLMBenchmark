from typing import List

from evaluate_config import DEFAULT_EVAL_CRITERIA


CRITERIA_DESCRIPTIONS = {
    "grammar_quality": "grammar, spacing, punctuation, awkward wording",
    "naturalness_quality": "whether the notification sounds like a realistic user-facing message",
    "title_quality": "whether title-like content is natural rather than a synthetic summary label",
    "format_consistency": "structure, line breaks, delimiter consistency, field formatting consistency",
    "semantic_preservation_risk": "risk that the sample contains confusing wording that may distort original meaning",
}


def build_eval_system_rules(criteria: List[str] | None = None) -> str:
    criteria = criteria or list(DEFAULT_EVAL_CRITERIA)
    criteria_lines = []
    json_lines = []
    for name in criteria:
        desc = CRITERIA_DESCRIPTIONS.get(name, name)
        criteria_lines.append(f"- {name}: {desc}")
        json_lines.append(f'    "{name}": {{"score": 1-5, "reason": "..."}}')

    return (
        "You are a strict evaluator for reservation-notification dataset quality.\n\n"
        "Evaluate each sample on the following criteria only:\n"
        + "\n".join(criteria_lines)
        + "\n\n"
        + "Important rules:\n"
        + "- Do not change the sample.\n"
        + "- Do not judge business correctness unless it is directly visible from the text itself.\n"
        + "- Focus on quality of the dataset text.\n"
        + "- Be specific and evidence-based.\n\n"
        + "Return strict JSON:\n"
        + "{\n"
        + '  "overall_score": 1-5,\n'
        + '  "criteria": {\n'
        + ",\n".join(json_lines)
        + "\n  },\n"
        + '  "major_issues": ["..."],\n'
        + '  "improvement_suggestions": ["..."],\n'
        + '  "summary": "..."\n'
        + "}"
    )


def build_eval_prompt(text: str, criteria: List[str] | None = None) -> str:
    return build_eval_system_rules(criteria) + "\n\nEvaluate this sample in detail.\n\n[SAMPLE]\n" + text
