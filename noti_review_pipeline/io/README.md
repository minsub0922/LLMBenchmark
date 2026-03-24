# io

I/O helpers for the notification review pipeline.

## Responsibility
- load JSONL input samples
- save improved JSONL output
- save CSV audit tables
- save Excel history and review sheets

## Main file
- `artifacts.py`

## Notes
Keep business logic out of this module. This package should only handle serialization and file output.
