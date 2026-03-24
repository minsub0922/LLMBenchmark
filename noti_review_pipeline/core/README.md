# core

Core review logic is grouped here.

## Responsibility
- build prompts for remote review
- parse model outputs
- decide whether a sample should be kept or lightly improved
- track per-row change history and audit records
- orchestrate multi-pass review runs

## Recommended files
- `prompts.py`
- `logic.py`
- `history.py`
- `review_engine.py`

## Boundary
This module should not own low-level HTTP transport or generic file I/O.
