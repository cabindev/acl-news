"""Tavily search — Thai + English, news + feature articles, run in parallel."""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from tavily import TavilyClient

import config
from tools.history import load_published_urls

MAX_AGE_DAYS = config.MAX_AGE_DAYS

# Profiles restricted to Thai-language sources only.
THAI_ONLY_PROFILES = {"funeral"}
# Profiles that use evergreen content (topic=general, no ≤7-day limit).
EVERGREEN_PROFILES = {"funeral"}
_THAI_RE = re.compile(r"[฀-๿]")


def _has_thai(text: str) -> bool:
    return bool(_THAI_RE.search(text or ""))


def _within_max_age(published_date: str) -> bool:
    """True if published within MAX_AGE_DAYS. Unparseable/empty dates pass
    (Tavily already constrains by days=7; this is a best-effort safety net)."""
    if not published_date:
        return True
    dt = None
    for parse in (parsedate_to_datetime,
                  lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))):
        try:
            dt = parse(published_date)
            break
        except Exception:
            continue
    if dt is None:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)

# ── Query sets per region ─────────────────────────────────────────────────────
# Thailand-focused.
THAI_NEWS_QUERIES = [
    "ข่าว เครื่องดื่มแอลกอฮอล์ ไทย ล่าสุด",
    "พ.ร.บ. ควบคุมเครื่องดื่มแอลกอฮอล์ กฎหมาย นโยบาย ไทย",
    "ภาษีสรรพสามิต สุรา เบียร์ ไทย",
    "เมาแล้วขับ อุบัติเหตุ สงกรานต์ ปีใหม่ ไทย",
    "งดเหล้าเข้าพรรษา สสส. รณรงค์ ลดการดื่ม",
    "เยาวชน นักดื่มหน้าใหม่ ผลกระทบ แอลกอฮอล์ ไทย",
]
THAI_ARTICLE_QUERIES = [
    "บทความ แอลกอฮอล์ ผลกระทบต่อสุขภาพ สังคมไทย",
    "เครื่องดื่มแอลกอฮอล์ ครอบครัว ความรุนแรง ปัญหาสังคม ไทย",
    "งานวิจัย โทษของแอลกอฮอล์ สุขภาวะ ไทย",
]

# International / global.
INTL_NEWS_QUERIES = [
    "alcohol policy regulation public health news",
    "alcohol law enforcement drink driving news",
    "alcohol public health drinking harm study latest",
    "alcohol control tax ban regulation country news",
]
INTL_ARTICLE_QUERIES = [
    "alcohol health effects explainer research insight",
    "alcohol and society public health feature article",
]

# Alcohol-free funerals (งานศพปลอดเหล้า) + the problems alcohol causes at funerals.
FUNERAL_NEWS_QUERIES = [
    "งานศพปลอดเหล้า ชุมชน วัด ต้นแบบ",
    "งดเหล้าในงานศพ รณรงค์ สสส.",
    "งานศพ สิ้นเปลือง เป็นหนี้ ยืมเงิน ค่าเหล้า",
    "ค่าใช้จ่ายงานศพ เหล้า สุรา ภาระครอบครัว",
]
FUNERAL_ARTICLE_QUERIES = [
    "บทความ งานศพปลอดเหล้า ประโยชน์ วิธีจัด",
    "งานศพปลอดเหล้า ตัวอย่าง ครอบครัว ชุมชน ไทย",
    "ปัญหา งานศพ จัดใหญ่ สิ้นเปลือง หนี้สิน เหล้า",
]


def _queries_for(profile: str) -> tuple[list[str], list[str]]:
    """Return (news_queries, article_queries) for a profile."""
    if profile == "intl":
        return INTL_NEWS_QUERIES, INTL_ARTICLE_QUERIES
    if profile == "funeral":
        return FUNERAL_NEWS_QUERIES, FUNERAL_ARTICLE_QUERIES
    return THAI_NEWS_QUERIES, THAI_ARTICLE_QUERIES


def _search_one(client: TavilyClient, query: str, kind: str,
                topic: str, days: int | None) -> list[dict]:
    # topic="news" → carries published_date + recency-constrained (intl/thai);
    # topic="general" → evergreen results for awareness topics (funeral).
    params = dict(query=query, search_depth="advanced", topic=topic,
                  max_results=config.MAX_RESULTS_PER_QUERY,
                  include_raw_content=True)
    if days is not None:
        params["days"] = days
    try:
        resp = client.search(**params)
    except Exception as exc:  # noqa: BLE001 - one bad query shouldn't kill the run
        print(f"  ! Tavily query failed ({query[:40]}...): {exc}")
        return []

    out = []
    for r in resp.get("results", []):
        # Prefer the full page text (raw_content); fall back to the snippet.
        raw = (r.get("raw_content") or "").strip()
        snippet = (r.get("content") or "").strip()
        out.append(
            {
                "title": r.get("title", "").strip(),
                "url": r.get("url", "").strip(),
                "content": raw or snippet,
                "score": r.get("score", 0),
                "published_date": r.get("published_date", ""),
                "query": query,
                "kind": kind,
            }
        )
    return out


def search_alcohol_news(region: str = "thai") -> list[dict]:
    """Run news + feature-article queries in parallel, dedupe, return list.

    `region` is 'thai' or 'intl' and selects the query set. Both news and
    articles are constrained to ≤7 days (server-side via days=7 and again by
    the age filter below)."""
    if not config.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not set")

    news_queries, article_queries = _queries_for(region)
    evergreen = region in EVERGREEN_PROFILES
    thai_only = region in THAI_ONLY_PROFILES
    topic = "general" if evergreen else "news"
    days = None if evergreen else MAX_AGE_DAYS

    client = TavilyClient(api_key=config.TAVILY_API_KEY)
    # (query, kind, topic, days)
    jobs = [(q, "news", topic, days) for q in news_queries] + \
           [(q, "article", topic, days) for q in article_queries]

    articles: list[dict] = []
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        for batch in pool.map(lambda j: _search_one(client, *j), jobs):
            articles.extend(batch)

    # Dedupe by URL (keep highest score). Age filter applies to non-evergreen.
    # Thai-only profiles also drop items with no Thai text in the title/content.
    by_url: dict[str, dict] = {}
    for a in articles:
        if not a["url"]:
            continue
        if not evergreen and not _within_max_age(a.get("published_date", "")):
            continue
        if thai_only and not (_has_thai(a.get("title", "")) or _has_thai(a.get("content", "")[:400])):
            continue
        prev = by_url.get(a["url"])
        if prev is None or a["score"] > prev["score"]:
            by_url[a["url"]] = a

    ranked = sorted(by_url.values(), key=lambda a: a["score"], reverse=True)

    # Drop items already published in a previous run (avoid Telegram repeats).
    seen = load_published_urls()
    fresh = [a for a in ranked if a["url"] not in seen]
    if fresh:                       # keep all if filtering would empty the list
        ranked = fresh

    n_news = sum(1 for a in ranked if a["kind"] == "news")
    n_art = len(ranked) - n_news
    window = "evergreen" if evergreen else f"≤{MAX_AGE_DAYS}d"
    thai_tag = " thai-only" if thai_only else ""
    print(f"  → Tavily [{region}] returned {len(ranked)} items {window}{thai_tag} "
          f"({n_news} news, {n_art} articles, {len(seen)} already published)")
    return ranked
