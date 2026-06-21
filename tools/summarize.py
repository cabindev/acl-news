"""Gemini Flash — summarize every article in parallel into Thai briefing bullets."""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor

from google import genai
from google.genai import types

import config

_PROMPT = """คุณเป็นบรรณาธิการข่าวด้านแอลกอฮอล์ สรุปข่าวต่อไปนี้เป็นภาษาไทยแบบกระชับ
ตอบกลับเป็น JSON เท่านั้น ตามรูปแบบนี้:
{{"headline_th": "พาดหัวภาษาไทยสั้นๆ ไม่เกิน 22 ตัวอักษร กระชับน่าสนใจ", "summary_th": "สรุป 2-3 ประโยค", "category": "นโยบาย|สุขภาพ|อุตสาหกรรม|สังคม", "relevance": 0-10}}

หัวข้อ: {title}
เนื้อหา: {content}
"""


def _extract_json(text: str) -> dict:
    """Extract JSON from response text robustly."""
    text = text.strip()
    # Strip markdown code blocks
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
        if "```" in text:
            text = text[: text.index("```")]
    # Find first {...} block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    return json.loads(text)


def _summarize_one(client: genai.Client, article: dict) -> dict:
    try:
        response = client.models.generate_content(
            model=config.SUMMARIZER_MODEL,
            contents=_PROMPT.format(
                title=article.get("title", ""),
                content=article.get("content", "")[:4000],
            ),
            config=types.GenerateContentConfig(
                max_output_tokens=512,
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        data = _extract_json(response.text)
    except Exception as exc:  # noqa: BLE001
        print(f"  ! Summary failed ({article.get('title','')[:40]}...): {exc}")
        data = {
            "headline_th": article.get("title", ""),
            "summary_th": article.get("content", "")[:200],
            "category": "สังคม",
            "relevance": int(article.get("score", 0) * 10),
        }

    return {**article, **data}


_FB_PROMPT = """คุณเป็นกองบรรณาธิการเพจ CivicSpace เขียน "โพสต์เฟซบุ๊ก" ภาษาไทยจากข่าวต่อไปนี้
ข้อกำหนด:
- กระชับ น่าอ่าน ความยาว 2-4 ย่อหน้า
- เปิดด้วยประเด็นที่ดึงดูดความสนใจ ให้ข้อมูล/ตัวเลขสำคัญ และชี้ให้เห็นนัยต่อสังคมหรือสุขภาพ
- น้ำเสียงให้ความรู้ เป็นกลาง น่าเชื่อถือ เหมาะกับเพจสาธารณะ
- ห้ามใส่ลิงก์ ห้ามใส่แฮชแท็ก ไม่ต้องมีหัวข้อกำกับ
ตอบกลับเฉพาะเนื้อโพสต์เท่านั้น

หัวข้อ: {title}
เนื้อหา: {content}
"""


def compose_fb_post(article: dict) -> str:
    """Write a ready-to-post Thai Facebook caption for one approved story.

    Uses plain text generation (not function calling) so long Thai copy is not
    truncated. No link/hashtag — those are appended deterministically later.
    """
    client = genai.Client(api_key=config.GOOGLE_API_KEY)
    try:
        response = client.models.generate_content(
            model=config.SUMMARIZER_MODEL,
            contents=_FB_PROMPT.format(
                title=article.get("title", ""),
                content=article.get("content", "")[:6000],
            ),
            config=types.GenerateContentConfig(
                max_output_tokens=2048,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        post = (response.text or "").strip()
    except Exception as exc:  # noqa: BLE001
        print(f"  ! FB post composition failed: {exc}")
        post = article.get("summary_th", "") or article.get("headline_th", "")
    return post


def summarize_articles(articles: list[dict]) -> list[dict]:
    """Summarize all articles concurrently with Gemini Flash."""
    if not config.GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set")

    client = genai.Client(api_key=config.GOOGLE_API_KEY)
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(articles)))) as pool:
        summarized = list(pool.map(lambda a: _summarize_one(client, a), articles))

    print(f"  → Summarized {len(summarized)} articles with {config.SUMMARIZER_MODEL}")
    return summarized
