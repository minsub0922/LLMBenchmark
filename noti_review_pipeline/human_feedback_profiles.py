from typing import Dict


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
}


def get_feedback_instruction(profile: str) -> str:
    return HUMAN_FEEDBACK_PROFILES.get(profile, "")
