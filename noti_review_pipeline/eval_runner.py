from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

from eval_parser import parse_eval_response
from eval_prompt_builder import build_eval_prompt
from eval_reporter import flatten_eval_result
from remote_client import RemoteInferenceClient



def evaluate_one(
    client: RemoteInferenceClient,
    row_id: int,
    record: Dict[str, Any],
    criteria: List[str] | None = None,
) -> Tuple[int, Dict[str, Any]]:
    """
    Evaluate one dataset row.

    Parameters
    ----------
    client:
        Remote inference client.
    row_id:
        Input row index.
    record:
        Raw input record. Must contain `text` for current pipeline.
    criteria:
        Optional subset of criteria to use in the prompt.

    Returns
    -------
    (row_id, flattened_result)
    """
    text = str(record.get("text", ""))
    prompt = build_eval_prompt(text=text, criteria=criteria)
    raw = client.generate(prompt)
    parsed = parse_eval_response(raw)
    row = flatten_eval_result(row_id=row_id, text=text, result=parsed)
    return row_id, row



def run_parallel_evaluation(
    records: List[Dict[str, Any]],
    client: RemoteInferenceClient,
    workers: int,
    criteria: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Run row-level evaluation in parallel while preserving original order.
    """
    rows: List[Dict[str, Any]] = [None] * len(records)  # type: ignore
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [
            ex.submit(evaluate_one, client, idx, rec, criteria)
            for idx, rec in enumerate(records)
        ]
        for fut in as_completed(futures):
            idx, row = fut.result()
            rows[idx] = row
    return rows
