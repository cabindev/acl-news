"""Published-story history — prevents re-posting the same item across runs."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config

_PATH = config.OUTPUT_DIR / "published.json"
RETENTION_DAYS = 45            # don't repeat a story within this window


def _load() -> list[dict]:
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def _is_recent(entry: dict, cutoff: datetime) -> bool:
    try:
        return datetime.fromisoformat(entry.get("published_at", "")) >= cutoff
    except Exception:
        return True   # keep entries with unparseable dates


def load_published_urls() -> set[str]:
    """URLs published within the retention window."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    return {e["url"] for e in _load()
            if e.get("url") and _is_recent(e, cutoff)}


def record_published(url: str, headline: str = "") -> None:
    """Append a freshly published story and prune entries past retention."""
    if not url:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    entries = [e for e in _load() if _is_recent(e, cutoff)]
    entries.append({
        "url": url,
        "headline": headline,
        "published_at": datetime.now(timezone.utc).isoformat(),
    })
    _PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2),
                     encoding="utf-8")
