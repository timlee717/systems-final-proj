import json
import os
from typing import Set

DATA_FILE = os.getenv("DATA_FILE", "data/survey.ndjson")

_seen_ids: Set[str] = set()


def _load_seen_ids() -> None:
    """Populate the in-memory set of known submission_ids for dedupe."""
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sid = obj.get("submission_id")
                if isinstance(sid, str):
                    _seen_ids.add(sid)
    except OSError:
        # If we can't read the file, just start fresh in memory.
        return


# Load any existing ids on import
_load_seen_ids()


def append_record(record: dict) -> bool:
    """
    Append one JSON record to the NDJSON file.

    Returns:
        True  -> record was written
        False -> duplicate (same submission_id), not written
    """
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

    submission_id = record.get("submission_id")
    if isinstance(submission_id, str) and submission_id in _seen_ids:
        return False

    try:
        with open(DATA_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        # If we can't write, treat as failure.
        return False

    if isinstance(submission_id, str):
        _seen_ids.add(submission_id)

    return True
