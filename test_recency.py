#!/usr/bin/env python3
"""Verify the ≤7-day recency filter actually works.

    python test_recency.py          # fast unit checks (no API)
    python test_recency.py --live   # also audit real Tavily news results

Unit checks pin _within_max_age() behaviour across date formats and ages.
The optional live audit asserts every dated NEWS item returned is ≤7 days old.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from tools.search import MAX_AGE_DAYS, _within_max_age, search_alcohol_news

now = datetime.now(timezone.utc)


def _iso(days_ago: float) -> str:
    return (now - timedelta(days=days_ago)).isoformat()


def _rfc(days_ago: float) -> str:
    # RFC 2822 style, e.g. "Wed, 18 Jun 2026 10:00:00 +0000"
    return (now - timedelta(days=days_ago)).strftime("%a, %d %b %Y %H:%M:%S +0000")


# (label, published_date, expected_within_7_days)
CASES = [
    ("today (ISO)",            _iso(0),     True),
    ("3 days ago (ISO)",       _iso(3),     True),
    ("6.9 days ago (ISO)",     _iso(6.9),   True),
    ("8 days ago (ISO)",       _iso(8),     False),
    ("30 days ago (ISO)",      _iso(30),    False),
    ("2 days ago (RFC2822)",   _rfc(2),     True),
    ("10 days ago (RFC2822)",  _rfc(10),    False),
    ("ISO with Z suffix",      (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"), True),
    ("empty string",           "",          True),   # lenient: Tavily days=7 already constrains
    ("malformed",              "not a date", True),  # lenient: keep rather than wrongly drop
]


def run_unit() -> bool:
    print(f"== Unit checks (MAX_AGE_DAYS = {MAX_AGE_DAYS}) ==")
    ok = True
    for label, value, expected in CASES:
        got = _within_max_age(value)
        status = "PASS" if got == expected else "FAIL"
        if got != expected:
            ok = False
        print(f"  [{status}] {label:24s} → {got} (expected {expected})")
    return ok


def run_live() -> bool:
    print("\n== Live audit (real Tavily results) ==")
    ok = True
    for region in ("thai", "intl"):
        items = search_alcohol_news(region)
        for kind in ("news", "article"):
            sub = [a for a in items if a.get("kind") == kind]
            offenders = [(a.get("published_date", ""), a.get("url", "")) for a in sub
                         if a.get("published_date") and not _within_max_age(a["published_date"])]
            dated = sum(1 for a in sub if a.get("published_date"))
            print(f"  [{region}] {kind:8s} total={len(sub):2d} dated={dated:2d} "
                  f"undated={len(sub)-dated:2d} stale={len(offenders)}")
            for pd, url in offenders:
                ok = False
                print(f"      STALE: {pd}  {url}")
    return ok


def main() -> int:
    ok = run_unit()
    if "--live" in sys.argv:
        ok = run_live() and ok
    print("\n" + ("✅ ALL PASS" if ok else "❌ FAILURES FOUND"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
