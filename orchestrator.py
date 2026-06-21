"""Gemini orchestrator using google-genai SDK.

Gemini acts as the CivicSpace editorial board, driving the pipeline through
function calling: search → summarize → pick the single most newsworthy story
(published within 7 days) → write a ready-to-post Facebook caption →
approve & publish. One transparent headline card is rendered for the story.
"""
from __future__ import annotations

import json
from pathlib import Path

from google import genai
from google.genai import types

import config
from tools.deliver import approve_and_publish
from tools.search import search_alcohol_news
from tools.summarize import compose_fb_post, summarize_articles

_ROOT = Path(__file__).resolve().parent

# Per-profile editorial rules file (the "editorial board" for that topic).
_RULES_FILES = {
    "funeral": "RULES_funeral.md",
}


def _load_rules(profile: str = "thai") -> str:
    """Editorial policy for the profile — editable without code changes."""
    path = _ROOT / _RULES_FILES.get(profile, "RULES.md")
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _scope_directive(profile: str) -> str:
    """Per-run scope appended to the system prompt."""
    if profile == "intl":
        scope = "ข่าว/บทความต่างประเทศ (ทั่วโลก ไม่ใช่ข่าวไทย)"
    elif profile == "funeral":
        scope = ("เฉพาะหัวข้อ \"งานศพปลอดเหล้า\" หรือปัญหาการจัดงานศพที่เกี่ยวกับเหล้า "
                 "(จ่ายแพง/เป็นหนี้/สิ้นเปลือง) ในไทย")
    else:
        scope = "ข่าว/บทความในประเทศไทย หรือประเด็นที่เกี่ยวข้องกับไทยโดยตรง"
    return (f"\n\n=== ขอบเขตรอบนี้ ===\nรอบนี้ให้เลือกเฉพาะ \"{scope}\" เท่านั้น "
            f"ห้ามเลือกชิ้นที่อยู่นอกขอบเขตนี้")

SYSTEM = """คุณคือ "กองบรรณาธิการบริหาร" ของเพจ CivicSpace ดูแลคอนเทนต์ข่าวแอลกอฮอล์
ทำงานตามขั้นตอนนี้โดยใช้ tools ที่มีให้:

1. เรียก search_alcohol_news เพื่อค้นข่าว
2. เรียก summarize_articles เพื่อสรุปทั้งหมด (จะได้ index, headline_th, category, relevance, url, published_date, kind)
3. ทำหน้าที่บรรณาธิการ: คัดเลือก "ชิ้นที่น่าสนใจที่สุดเพียง 1 ชิ้น" ตาม "กฎกองบรรณาธิการ" ด้านล่างอย่างเคร่งครัด
   - เลือกได้ทั้งข่าว (kind=news) และบทความ/สกู๊ป (kind=article) ทั้งในและต่างประเทศ
   - ถ้าเป็นข่าว (news) ต้องเผยแพร่ไม่เกิน 7 วัน (ดู published_date); บทความ (article) ไม่จำกัดอายุ
   - ยึดพันธกิจและเกณฑ์ "เน้น/ไม่สนใจ" ตามกฎ ถ้าอันดับต้นเข้าข่าย "ไม่สนใจ" ให้ข้ามไปชิ้นถัดไป
4. เรียก approve_and_publish เพื่ออนุมัติเผยแพร่ลงเฟซบุ๊ก พร้อม:
   - chosen_index: index ข่าวที่อนุมัติ
   - headline: พาดหัวสั้นกระชับ ≤22 ตัวอักษร สำหรับการ์ด
   - editor_note: เหตุผลเชิงบรรณาธิการที่อนุมัติข่าวนี้ สั้นๆ 1 ประโยค
   (ระบบจะร่างโพสต์เฟซบุ๊กฉบับเต็มจากข่าว แล้วแนบที่มาและ #CivicSpace ให้อัตโนมัติ)

**สำคัญ:** ถ้าไม่มีชิ้นใดตรงพันธกิจและขอบเขตของรอบนี้จริงๆ **ห้ามฝืนเลือก** ให้เรียก skip_publication
พร้อมเหตุผลแทน — การไม่เผยแพร่ดีกว่าเผยแพร่เนื้อหาที่หลุดหัวข้อ

เรียก approve_and_publish หรือ skip_publication อย่างใดอย่างหนึ่งเพียงครั้งเดียว และทำให้ครบทุกขั้นตอน"""

_FUNCTION_DECLARATIONS = [
    types.FunctionDeclaration(
        name="search_alcohol_news",
        description="ค้นข่าวแอลกอฮอล์ผ่าน Tavily คืนจำนวนข่าวที่พบ",
        parameters=types.Schema(type="OBJECT", properties={}),
    ),
    types.FunctionDeclaration(
        name="summarize_articles",
        description="สรุปข่าวทั้งหมดด้วย Gemini Flash คืนรายการสรุปพร้อม index, headline_th, category, relevance, url, published_date",
        parameters=types.Schema(type="OBJECT", properties={}),
    ),
    types.FunctionDeclaration(
        name="approve_and_publish",
        description="อนุมัติข่าว 1 ข่าวเพื่อเผยแพร่ลงเฟซบุ๊ก: สร้างการ์ดพาดหัว + โพสต์พร้อมคัดลอก (แนบที่มา + #CivicSpace) + ส่ง Telegram — เรียกเพียงครั้งเดียว",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "chosen_index": types.Schema(type="INTEGER", description="index ของข่าวที่อนุมัติเผยแพร่"),
                "headline": types.Schema(type="STRING", description="พาดหัวสั้น ≤22 ตัวอักษร สำหรับการ์ด"),
                "editor_note": types.Schema(type="STRING", description="เหตุผลเชิงบรรณาธิการที่อนุมัติ สั้นๆ"),
            },
            required=["chosen_index", "headline"],
        ),
    ),
    types.FunctionDeclaration(
        name="skip_publication",
        description="ข้ามรอบนี้โดยไม่เผยแพร่ เมื่อไม่มีชิ้นใดตรงพันธกิจ/ขอบเขตจริงๆ — เรียกแทน approve_and_publish",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "reason": types.Schema(type="STRING", description="เหตุผลที่ไม่มีชิ้นที่เหมาะสม"),
            },
            required=["reason"],
        ),
    ),
]


class State:
    def __init__(self, region: str = "thai") -> None:
        self.region = region
        self.articles: list[dict] = []
        self.summaries: list[dict] = []
        self.result: dict | None = None


def _dispatch(name: str, args: dict, state: State) -> str:
    if name == "search_alcohol_news":
        state.articles = search_alcohol_news(state.region)
        return json.dumps({"found": len(state.articles)}, ensure_ascii=False)

    if name == "summarize_articles":
        state.summaries = summarize_articles(state.articles)
        compact = [
            {
                "index": i,
                "headline_th": s.get("headline_th", ""),
                "category": s.get("category", ""),
                "relevance": s.get("relevance", 0),
                "url": s.get("url", ""),
                "published_date": s.get("published_date", ""),
                "kind": s.get("kind", "news"),
            }
            for i, s in enumerate(state.summaries)
        ]
        return json.dumps(compact, ensure_ascii=False)

    if name == "skip_publication":
        if state.result:
            return json.dumps({"status": "already_done"}, ensure_ascii=False)
        state.result = {"skipped": True, "reason": args.get("reason", "")}
        return json.dumps({"status": "skipped"}, ensure_ascii=False)

    if name == "approve_and_publish":
        # Guard: only publish once
        if state.result:
            return json.dumps({"status": "already_published"}, ensure_ascii=False)
        idx = args["chosen_index"]
        if not (0 <= idx < len(state.summaries)):
            return json.dumps({"error": "chosen_index out of range"}, ensure_ascii=False)
        story = state.summaries[idx]
        briefing = {
            "story": story,
            "headline": args.get("headline", ""),
            "fb_post": compose_fb_post(story),
            "editor_note": args.get("editor_note", ""),
            "region": state.region,
        }
        state.result = approve_and_publish(briefing)
        state.result["briefing"] = briefing
        return json.dumps({"status": "published", **state.result}, ensure_ascii=False)

    return json.dumps({"error": f"unknown tool {name}"})


def run(region: str = "thai") -> dict:
    client = genai.Client(api_key=config.GOOGLE_API_KEY)
    state = State(region)
    rules = _load_rules(region)

    system = (f"{SYSTEM}\n\n=== กฎกองบรรณาธิการ (ต้องปฏิบัติตาม) ===\n{rules}"
              if rules else SYSTEM) + _scope_directive(region)

    tool = types.Tool(function_declarations=_FUNCTION_DECLARATIONS)
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        tools=[tool],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY")
        ),
        max_output_tokens=8192,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    contents: list = [
        types.Content(role="user", parts=[types.Part(text="เริ่มทำ Alcohol Briefing ประจำวันนี้ได้เลย")])
    ]

    for _step in range(12):
        response = client.models.generate_content(
            model=config.ORCHESTRATOR_MODEL,
            contents=contents,
            config=cfg,
        )

        candidate = response.candidates[0]
        contents.append(candidate.content)

        fn_calls = [p.function_call for p in candidate.content.parts if p.function_call]
        for p in candidate.content.parts:
            if p.text and p.text.strip():
                print(f"  [Gemini] {p.text.strip()}")

        if not fn_calls:
            break

        fn_parts = []
        for fc in fn_calls:
            print(f"  ⚙ {fc.name}")
            result = _dispatch(fc.name, dict(fc.args), state)
            fn_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=fc.name,
                        response={"result": result},
                    )
                )
            )

        contents.append(types.Content(role="user", parts=fn_parts))

        # Stop immediately after successful delivery
        if state.result:
            break

    if not state.result:
        raise RuntimeError("Orchestrator finished without delivering a briefing")
    return state.result
