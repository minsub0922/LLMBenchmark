import json
import time
from typing import Any, Dict

import requests


class RemoteInferenceClient:
    def __init__(self, endpoint: str, model: str, timeout: int, max_retries: int, retry_sleep: float):
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_sleep = retry_sleep

    def generate(self, text: str) -> str:
        payload = {
            "model": self.model,
            "text": text,
        }
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                r = requests.post(
                    self.endpoint,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    timeout=self.timeout,
                )
                r.raise_for_status()
                data: Dict[str, Any] = r.json()
                if isinstance(data, dict):
                    for key in ["text", "response", "generated_text", "output"]:
                        if key in data and isinstance(data[key], str):
                            return data[key]
                return json.dumps(data, ensure_ascii=False)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_sleep)
        raise RuntimeError(f"Remote inference failed after retries: {last_error}")
