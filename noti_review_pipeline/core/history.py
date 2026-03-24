from typing import Any, Dict, List


def build_history_sheet(review_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    history_rows: List[Dict[str, Any]] = []
    for row in review_rows:
        history_rows.append(
            {
                'row_id': row.get('row_id', ''),
                'pass_idx': row.get('pass_idx', ''),
                'decision': row.get('decision', ''),
                'changed': row.get('changed', ''),
                'change_type': row.get('change_type', ''),
                'issues': row.get('issues', ''),
                'reason': row.get('reason', ''),
                'grammar_score': row.get('grammar_score', ''),
                'naturalness_score': row.get('naturalness_score', ''),
                'title_quality_score': row.get('title_quality_score', ''),
                'format_consistency_score': row.get('format_consistency_score', ''),
                'original_text': row.get('original_text', ''),
                'final_text': row.get('final_text', ''),
            }
        )
    return history_rows
