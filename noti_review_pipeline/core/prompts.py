from profiles.feedback_profiles import get_feedback_profile

BASE_SYSTEM_RULES = """
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
  "change_type": ["grammar_fix" | "title_rewrite" | "format_cleanup" | "keep"],
  "quality_scores": {
    "grammar": 1-5,
    "naturalness": 1-5,
    "title_quality": 1-5,
    "format_consistency": 1-5
  },
  "reason": "brief explanation"
}
""".strip()


def build_review_prompt(text: str, checks: list[str], feedback_profile: str = 'none') -> str:
    profile = get_feedback_profile(feedback_profile)
    profile_block = ''
    if profile.get('rules'):
        joined = '\n'.join(f'- {rule}' for rule in profile['rules'])
        profile_block = f"\n\nAdditional profile rules ({profile['name']}):\n{joined}"

    return (
        BASE_SYSTEM_RULES
        + profile_block
        + "\n\n"
        + f"Active checks: {', '.join(checks)}\n\n"
        + "Review this sample and improve it only if needed.\n\n"
        + "[SAMPLE]\n"
        + text
    )
