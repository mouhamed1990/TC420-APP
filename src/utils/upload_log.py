"""
Upload Log — persists and reads TC420 program upload history to/from JSON.
Each entry records the date/time, mode name, success flag, and a short message.
"""
import json
import os
from datetime import datetime
from typing import List
from dataclasses import dataclass, asdict, field


LOG_FILE = os.path.join(os.path.expanduser("~"), ".tc420_upload_log.json")
MAX_ENTRIES = 500  # keep last N entries


@dataclass
class LogEntry:
    timestamp: str        # ISO-8601, e.g. "2026-03-02T12:30:00"
    mode_name: str
    success: bool
    message: str
    n_modes: int = 1      # how many modes were sent in this batch


def load_log() -> List[LogEntry]:
    """Load all entries from disk (newest first)."""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        entries = [LogEntry(**e) for e in raw]
        return entries
    except Exception:
        return []


def append_entry(entry: LogEntry) -> None:
    """Append one entry and trim to MAX_ENTRIES."""
    entries = load_log()
    entries.insert(0, entry)           # newest first
    entries = entries[:MAX_ENTRIES]
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in entries], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[UploadLog] Error saving log: {e}")


def log_upload(mode_name: str, success: bool, message: str, n_modes: int = 1) -> LogEntry:
    """Create, persist, and return a new log entry."""
    entry = LogEntry(
        timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        mode_name=mode_name,
        success=success,
        message=message,
        n_modes=n_modes,
    )
    append_entry(entry)
    return entry


def clear_log() -> None:
    """Delete all log entries."""
    try:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
    except Exception:
        pass
