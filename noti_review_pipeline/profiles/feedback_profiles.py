PROFILES = {
    'none': {
        'name': 'none',
        'description': 'No extra human-feedback profile is applied.',
        'rules': [],
    },
    'title_grammar_v1': {
        'name': 'title_grammar_v1',
        'description': 'Improve grammar and convert weak summary-like titles into natural reservation titles.',
        'rules': [
            'Fix obvious grammar and spacing issues only.',
            'If the title is too generic, rewrite it into a reservation-style title that reflects the main entity and reserved item.',
            'Do not change factual fields or labels.',
        ],
    },
    'title_content_coverage_v1': {
        'name': 'title_content_coverage_v1',
        'description': 'Ensure the title covers the key reserved entity when the original title is too short or generic.',
        'rules': [
            'Prefer titles such as การจอง <location> <reserved_item> when appropriate.',
            'Do not invent details that are not present in the sample.',
        ],
    },
    'title_grammar_coverage_v1': {
        'name': 'title_grammar_coverage_v1',
        'description': 'Combine grammar cleanup and title-content coverage rules.',
        'rules': [
            'Fix obvious grammar, spacing, punctuation, and malformed line breaks.',
            'Improve low-quality summary-like titles so they better match the content.',
            'Preserve all facts, labels, dates, times, ids, and addresses.',
        ],
    },
}


def get_feedback_profile(name: str):
    return PROFILES.get(name or 'none', PROFILES['none'])


def list_feedback_profiles():
    return sorted(PROFILES.keys())
