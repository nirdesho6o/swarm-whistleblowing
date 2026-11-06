from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


class EventLogger:
    """Append-only JSONL event logger for a single run."""

    def __init__(self, run_dir: Path, run_id: str):
        self.run_dir = run_dir
        self.run_id = run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._events_path = self.run_dir / "events.jsonl"
        self._raw_path = self.run_dir / "raw.jsonl"
        self._events_fh = open(self._events_path, "a")
        self._raw_fh = open(self._raw_path, "a")

    def log(
        self,
        round_num: int | None,
        agent: str | None,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        event = {
            "run_id": self.run_id,
            "round": round_num,
            "ts": time.time(),
            "agent": agent,
            "type": event_type,
            "payload": payload,
        }
        self._events_fh.write(json.dumps(event) + "\n")
        self._events_fh.flush()
        return event

    def log_raw(self, round_num: int, agent: str, prompt_hash: str, raw_output: str) -> None:
        record = {
            "run_id": self.run_id,
            "round": round_num,
            "ts": time.time(),
            "agent": agent,
            "prompt_hash": prompt_hash,
            "raw_output": raw_output,
        }
        self._raw_fh.write(json.dumps(record) + "\n")
        self._raw_fh.flush()

    def close(self) -> None:
        self._events_fh.close()
        self._raw_fh.close()


def load_events(path: Path) -> list[dict[str, Any]]:
    """Load all events from a JSONL file."""
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events
