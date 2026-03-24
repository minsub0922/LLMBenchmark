# config module

This module owns runtime configuration for the notification review pipeline.

## Responsibility
- define environment-backed defaults
- define the `ReviewConfig` dataclass
- generate stable output name suffixes
- keep CLI wrappers and internal pipeline code on the same config contract

## Main file
- `settings.py`: canonical configuration source

## Notes
- The root-level `config.py` remains as a backward-compatible shim.
- New code should import from `noti_review_pipeline.config.settings`.

## Example
```python
from noti_review_pipeline.config.settings import ReviewConfig

cfg = ReviewConfig(
    input_file="data/reservation_th.jsonl",
    output_dir="results/run1",
    checks=["grammar", "title_summary"],
)
print(cfg.run_slug())
```
