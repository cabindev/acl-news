#!/usr/bin/env python3
"""Alcohol Briefing — entry point.

    python main.py

Orchestrated by Gemini: Tavily search → Gemini Flash summaries → editorial
selection → transparent typography card → compile (.md/.json) + Telegram delivery.
"""
from __future__ import annotations

import sys

import config


def preflight() -> bool:
    missing = config.require("GOOGLE_API_KEY", "TAVILY_API_KEY")
    if missing:
        print("✖ Missing required keys in .env: " + ", ".join(missing))
        print("  Copy .env.example to .env and fill them in.")
        return False

    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        print("ℹ Telegram not configured — delivery to Telegram will be skipped.")
    if not config.LOGO_PATH.exists():
        print("ℹ assets/logo_white.png not found — card will have no logo.")
    return True


def _region_from_args() -> str:
    """Region scope from argv: 'intl' or 'thai' (default thai)."""
    arg = (sys.argv[1].lower() if len(sys.argv) > 1 else "thai")
    if arg in ("intl", "international", "global", "world"):
        return "intl"
    return "thai"


def main() -> int:
    region = _region_from_args()
    label = "ต่างประเทศ" if region == "intl" else "ในไทย"
    print("=" * 56)
    print(f"  🍺  ALCOHOL BRIEFING — ข่าว{label} [{region}]")
    print("=" * 56)
    if not preflight():
        return 1

    # Imported here so a missing-key preflight exits before heavy imports.
    from orchestrator import run

    print(f"\n▶ Orchestrator ({config.ORCHESTRATOR_MODEL}) starting…\n")
    try:
        result = run(region)
    except Exception as exc:  # noqa: BLE001
        print(f"\n✖ Run failed: {exc}")
        return 2

    print("\n" + "=" * 56)
    print("  ✓ APPROVED FOR FACEBOOK")
    briefing = result.get("briefing", {})
    story = briefing.get("story", {})
    print(f"  Headline : {briefing.get('headline', '')}")
    if briefing.get("editor_note"):
        print(f"  Editor   : {briefing['editor_note']}")
    print(f"  Card     : {result.get('card')}")
    print(f"  Post     : {result.get('post')}")
    print(f"  Markdown : {result.get('markdown')}")
    print(f"  JSON     : {result.get('json')}")
    print("-" * 56)
    print("  โพสต์เฟซบุ๊ก (คัดลอกไปวางได้):\n")
    print(result.get("fb_post", ""))
    print("=" * 56)
    return 0


if __name__ == "__main__":
    sys.exit(main())
