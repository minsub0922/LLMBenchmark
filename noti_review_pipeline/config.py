from dataclasses import dataclass, field
from typing import List
import os


DEFAULT_ENDPOINT = os.environ.get(
    "ENDPOINT",
    "https://inference-aistudio-data-synthesis.shuttle-stg.sr-cloud.com/generate",
)
DEFAULT_MODEL = os.environ.get("MODEL", "qwen3.5-397b-a17b-fp8")
DEFAULT_BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "20"))
DEFAULT_WORKERS = int(os.environ.get("WORKERS", "4"))
DEFAULT_TIMEOUT = int(os.environ.get("TIMEOUT", "180"))
DEFAULT_MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
DEFAULT_RETRY_SLEEP = float(os.environ.get("RETRY_SLEEP", "2.0"))
DEFAULT_MAX_PASSES = int(os.environ.get("MAX_PASSES", "2"))
DEFAULT_MODE = os.environ.get("MODE", "full")
DEFAULT_DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
DEFAULT_CHECKS = os.environ.get(
    "CHECKS",
    "grammar,title_summary,field_consistency",
)

CHECK_ALIASES = {
    "grammer": "grammar",
    "grammar": "grammar",
    "title": "title_summary",
    "title_summary": "title_summary",
    "title_content_coverage": "title_content_coverage",
    "field_consistency": "field_consistency",
    "spacing": "spacing_punctuation",
    "spacing_punctuation": "spacing_punctuation",
    "broken_chars": "broken_characters",
    "broken_characters": "broken_characters",
    "format": "format_consistency",
    "format_consistency": "format_consistency",
}


def normalize_check_name(name: str) -> str:
    key = str(name or "").strip().lower()
    return CHECK_ALIASES.get(key, key)


@dataclass
class ReviewConfig:
    input_file: str
    output_dir: str
    endpoint: str = DEFAULT_ENDPOINT
    model: str = DEFAULT_MODEL
    batch_size: int = DEFAULT_BATCH_SIZE
    workers: int = DEFAULT_WORKERS
    timeout: int = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_sleep: float = DEFAULT_RETRY_SLEEP
    max_passes: int = DEFAULT_MAX_PASSES
    mode: str = DEFAULT_MODE
    dry_run: bool = DEFAULT_DRY_RUN
    checks: List[str] = field(default_factory=lambda: [x.strip() for x in DEFAULT_CHECKS.split(",") if x.strip()])

    def __post_init__(self) -> None:
        normalized: List[str] = []
        for item in self.checks or []:
            key = normalize_check_name(item)
            if key and key not in normalized:
                normalized.append(key)
        self.checks = normalized or ["grammar", "title_summary", "field_consistency"]

    def checks_slug(self) -> str:
        return "-".join(self.checks) if self.checks else "none"

    def run_slug(self) -> str:
        return f"{self.checks_slug()}__p{self.max_passes}__{self.mode}{'__dry' if self.dry_run else ''}"
