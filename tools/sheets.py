"""Log each published briefing to a Google Sheet via an Apps Script webhook.

Set SHEET_WEBHOOK_URL in .env to a Google Apps Script Web App that appends a
row (see README for the script). If unset, logging is skipped silently.
"""
from __future__ import annotations

import base64
import io
from datetime import datetime

import requests

import config


def _card_thumb_b64(path: str, width: int = 480, bg=(17, 17, 17)) -> str:
    """Composite the (transparent, white-text) card onto a dark background and
    downscale → base64 PNG, so it's visible and light enough to embed in Sheets."""
    try:
        from PIL import Image
        img = Image.open(path).convert("RGBA")
        flat = Image.new("RGB", img.size, bg)
        flat.paste(img, mask=img.split()[3])
        h = int(img.height * width / img.width)
        flat = flat.resize((width, h), Image.LANCZOS)
        buf = io.BytesIO()
        flat.save(buf, "PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as exc:  # noqa: BLE001
        print(f"  ! card thumbnail failed: {exc}")
        return ""

# Column order the Apps Script writes to the sheet.
COLUMNS = [
    "timestamp",
    "Title",
    "วันที่",
    "เนื้อหาข่าวที่สรุป",
    "ที่มาของข้อมูล",
    "รูปปก",
    "region",
    "kind",
    "category",
    "editor_note",
    "express_url",
    "วันที่เผยแพร่",      # actual article publish date (for verification)
]


def fmt_published(raw: str) -> str:
    """Normalise a Tavily published_date to YYYY-MM-DD; return raw on failure."""
    if not raw:
        return ""
    from datetime import datetime
    from email.utils import parsedate_to_datetime
    for parse in (parsedate_to_datetime,
                  lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))):
        try:
            return parse(raw).strftime("%Y-%m-%d")
        except Exception:
            continue
    return raw


def log_publication(briefing: dict, card: str = "", express_url: str = "") -> None:
    url = config.SHEET_WEBHOOK_URL
    if not url:
        print("  → Google Sheet logging skipped (SHEET_WEBHOOK_URL not set)")
        return

    story = briefing.get("story", {})
    now = datetime.now()
    
    # Extract summary content (Facebook post, with fallback to story summary)
    summary_content = briefing.get("fb_post_final") or briefing.get("fb_post") or story.get("summary_th", "")
    summary_content = summary_content.strip()

    row = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "Title": briefing.get("headline") or story.get("headline_th") or story.get("title", ""),
        "วันที่": now.strftime("%Y-%m-%d"),
        "เนื้อหาข่าวที่สรุป": summary_content,
        "ที่มาของข้อมูล": story.get("url", ""),
        "รูปปก": card,
        
        # Additional fields for compatibility
        "date": now.strftime("%Y-%m-%d"),
        "region": briefing.get("region", ""),
        "kind": story.get("kind", ""),
        "headline": briefing.get("headline") or story.get("headline_th", ""),
        "category": story.get("category", ""),
        "source": _source(story.get("url", "")),
        "url": story.get("url", ""),
        "editor_note": briefing.get("editor_note", ""),
        "express_url": express_url,
        "card": card,
        "วันที่เผยแพร่": fmt_published(story.get("published_date", "")),
    }
    payload = {"columns": COLUMNS, "row": row}
    if card:
        thumb = _card_thumb_b64(card)
        if thumb:
            payload["card_base64"] = thumb
    try:
        r = requests.post(url, json=payload, timeout=40)
        r.raise_for_status()
        print("  → Logged to Google Sheet")
    except Exception as exc:  # noqa: BLE001 — sheet logging must not break delivery
        print(f"  ! Google Sheet logging failed: {exc}")


def _source(u: str) -> str:
    from urllib.parse import urlparse
    try:
        net = urlparse(u).netloc.lower()
        return net[4:] if net.startswith("www.") else net
    except Exception:
        return ""
