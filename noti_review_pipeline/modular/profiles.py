from typing import Dict

HUMAN_FEEDBACK_PROFILES: Dict[str, str] = {
    'none': '',
    'title_grammar_v1': (
        'Apply these human-feedback-based preferences only when clearly supported by the sample text:\n'
        '1. If the title is a weak synthetic label, duplicated brand phrase, or generic confirmation phrase, rewrite the title to a more useful reservation-style title.\n'
        "2. Prefer the Thai title pattern 'การจอง {hotel_name} {room_type}' when both hotel/property name and room type are explicitly present in the sample.\n"
        "3. Remove duplicated booking-brand prefixes or generic phrases like 'การยืนยันการจอง' when a clearer reservation title can be formed.\n"
        '4. Improve wrong grammar, awkward Thai phrasing, spacing, and punctuation in the raw notification text.\n'
        '5. Do not invent hotel name, room type, date, or other facts that are not explicitly present.\n'
        '6. Keep semantic meaning, reservation status, ids, and all factual content unchanged.\n'
    ),
    'title_content_coverage_v1': (
        'Apply these title-content-coverage preferences only when clearly supported by the sample text:\n'
        "1. If the title is too generic, such as only 'การจอง', rewrite it so the main reserved entity is visible in the title.\n"
        '2. The rewritten title should cover the core content of the reservation, especially the venue, property, or service name explicitly shown in the sample.\n'
        "3. Prefer the compact Thai pattern 'การจอง {main_entity}' when the sample mainly provides one clear reserved entity.\n"
        "4. If both a clear property or service name and a clear room or item name are explicitly present, you may prefer 'การจอง {property_name} {room_or_item_name}' only when it remains natural and not overly long.\n"
        '5. Do not leave the title as a bare generic reservation label if the body clearly identifies what was reserved.\n'
        '6. Do not invent missing entities. Keep all factual content and meaning unchanged.\n'
    ),
    'title_grammar_coverage_v1': (
        'Combine grammar cleanup and title-content coverage rules when clearly supported by the sample text:\n'
        '1. Improve wrong grammar, awkward Thai phrasing, spacing, punctuation, and malformed line breaks in the raw notification text.\n'
        '2. If the title is generic or summary-like and does not cover the actual reservation content, rewrite it to expose the main reserved entity.\n'
        "3. Prefer 'การจอง {main_entity}' when the sample provides one clear venue, property, or service name.\n"
        "4. Prefer 'การจอง {hotel_name} {room_type}' when both hotel or property and room or item are explicitly present and the result is natural.\n"
        '5. Remove duplicated brand prefixes or generic confirmation wording when a clearer reservation title can be formed.\n'
        '6. Do not invent facts. Keep reservation status, ids, dates, times, entities, and semantics unchanged.\n'
    ),
}

def get_feedback_instruction(profile_name: str) -> str:
    return HUMAN_FEEDBACK_PROFILES.get(profile_name, '')
