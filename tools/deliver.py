"""Publish one approved story: render the card, build a ready-to-post Facebook
caption (source + #CivicSpace), write .md/.json/.txt, push to Telegram."""
from __future__ import annotations

import base64
import json
from datetime import date
from urllib.parse import urlparse

import requests

import config
from tools.history import record_published
from tools.sheets import log_publication
from tools.typography import generate_typography_card

HASHTAGS = "#CivicSpace"


def _source_of(url: str) -> str:
    """Human-friendly source from a URL — domain without the leading www."""
    try:
        net = urlparse(url).netloc.lower()
        return net[4:] if net.startswith("www.") else net
    except Exception:
        return ""


def _build_fb_post(briefing: dict) -> str:
    """Assemble the copy-paste Facebook caption: body + source + hashtag."""
    story = briefing.get("story", {})
    body = briefing.get("fb_post", "").strip()
    url = story.get("url", "").strip()

    parts = [body]
    if url:
        parts.append(f"\n📖 อ่านฉบับเต็ม: {url}")
    parts.append(f"\n{HASHTAGS}")
    return "\n".join(p for p in parts if p).strip()


def _render_markdown(briefing: dict, fb_post: str) -> str:
    d = date.today()
    story = briefing.get("story", {})
    lines = [
        f"# 🍺 Alcohol Briefing — {d:%d %B %Y}",
        "",
        f"**สถานะ:** ✅ APPROVED FOR FACEBOOK",
    ]
    if briefing.get("editor_note"):
        lines += [f"**บรรณาธิการ:** {briefing['editor_note']}", ""]
    else:
        lines += [""]

    lines += [f"## {story.get('headline_th', story.get('title', ''))}", ""]
    from tools.sheets import fmt_published
    pub = fmt_published(story.get("published_date", ""))
    if pub:
        lines += [f"*🗓 เผยแพร่: {pub}*", ""]
    if story.get("card_image"):
        lines += [f"![card]({story['card_image']})", ""]
    if briefing.get("express_url"):
        lines += [f"✏️ [แก้ไข/ออกแบบต่อใน Adobe Express]({briefing['express_url']})", ""]
    lines += [
        f"*หมวด: {story.get('category', '-')}*",
        "",
        "### โพสต์เฟซบุ๊ก (คัดลอกไปวางได้)",
        "",
        "```",
        fb_post,
        "```",
        "",
    ]
    return "\n".join(lines)


def _push_telegram(briefing: dict, fb_post: str, express_url: str = "") -> None:
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        print("  → Telegram delivery skipped (no token/chat id configured)")
        return

    story = briefing.get("story", {})
    api = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
    try:
        # Card with the headline as caption.
        card = story.get("card_image")
        if card:
            with open(card, "rb") as photo:
                r = requests.post(
                    f"{api}/sendPhoto",
                    data={"chat_id": config.TELEGRAM_CHAT_ID,
                          "caption": briefing.get("headline", "")[:1024]},
                    files={"photo": photo},
                    timeout=60,
                )
                r.raise_for_status()

        # Editorial banner + the ready-to-post caption (as a code block to copy).
        note = briefing.get("editor_note", "").strip()
        header = "✅ <b>APPROVED FOR FACEBOOK</b>"
        from tools.sheets import fmt_published
        pub = fmt_published(story.get("published_date", ""))
        if pub:
            header += f"\n🗓 เผยแพร่: {pub}  ·  {_source_of(story.get('url',''))}"
        if note:
            header += f"\n📝 {note}"
        message = f"{header}\n\n<pre>{_html_escape(fb_post)}</pre>"
        if express_url:
            message += (f'\n\n✏️ <a href="{express_url}">'
                        f"แก้ไข/ออกแบบการ์ดต่อใน Adobe Express</a>")

        r = requests.post(
            f"{api}/sendMessage",
            data={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": message[:4096],
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        r.raise_for_status()
        print("  → Telegram message sent")
    except Exception as exc:  # noqa: BLE001
        print(f"  ! Telegram delivery failed: {exc}")


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Adobe Fonts (Kanit) kit — resolves on the Express HTML importer.
_IMPORT_FONT_CSS = "https://use.typekit.net/srp1ays.css"


def build_import_html(headline: str, source: str = "") -> str:
    """Write a CLEAN, import-ready HTML card (title + source + wordmark) that
    Claude imports into Express via MCP → editable text layers. Short and
    self-contained (no base64), so it passes to the importer reliably."""
    source_txt = f"ที่มา: {source}".strip() if source else ""
    head = _html_escape(headline)
    src = _html_escape(source_txt)
    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8" />
  <title>CivicSpace Card</title>
  <meta name="hz:slide-selector" content=".card" />
  <meta name="hz:canvas-width" content="1080" />
  <meta name="hz:canvas-height" content="1350" />
  <link rel="stylesheet" href="{_IMPORT_FONT_CSS}" />
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #cfcfcf; }}
    .card {{ position: relative; width: 1080px; height: 1350px; background: transparent; overflow: hidden; font-family: "kanit", sans-serif; }}
    .scrim {{ position: absolute; left: 0; bottom: 0; width: 1080px; height: 560px; background: linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,0.45) 45%, rgba(0,0,0,0.82) 100%); }}
    .text {{ position: absolute; left: 64px; bottom: 64px; width: 952px; }}
    .headline {{ font-family: "kanit", sans-serif; font-weight: 900; font-size: 112px; line-height: 1.05; color: #ffffff; letter-spacing: -1px; text-shadow: 0 3px 12px rgba(0,0,0,0.45); }}
    .source {{ font-family: "kanit", sans-serif; font-weight: 300; font-size: 34px; color: #bcc6d0; margin-top: 28px; }}
    .brand {{ font-family: "kanit", sans-serif; font-weight: 500; font-size: 36px; letter-spacing: 4px; color: #f0d21e; margin-top: 14px; }}
  </style>
</head>
<body>
  <div class="card" data-canvas-width="1080" data-canvas-height="1350">
    <div class="scrim"></div>
    <div class="text">
      <div class="headline">{head}</div>
      {f'<div class="source">{src}</div>' if src else ''}
      <div class="brand">CIVIC SPACE</div>
    </div>
  </div>
</body>
</html>
"""
    out = config.OUTPUT_DIR / f"card-import-{date.today():%Y%m%d}.html"
    out.write_text(html, encoding="utf-8")
    return str(out)


def approve_and_publish(briefing: dict) -> dict:
    """Render the approved story's card, build the FB post, write files, deliver."""
    d = date.today()
    story = briefing.get("story", {})

    headline = briefing.get("headline") or story.get("headline_th", story.get("title", ""))
    source = _source_of(story.get("url", ""))

    # Card = Title + source only (no category/detail) — the headline stands
    # alone as a conversation opener.
    card = generate_typography_card(headline=headline, source=source)
    story["card_image"] = card

    fb_post = _build_fb_post(briefing)
    briefing["fb_post_final"] = fb_post

    md_path = config.OUTPUT_DIR / f"briefing-{d:%Y%m%d}.md"
    json_path = config.OUTPUT_DIR / f"briefing-{d:%Y%m%d}.json"
    post_path = config.OUTPUT_DIR / f"post-{d:%Y%m%d}.txt"
    html_path = config.OUTPUT_DIR / f"card-express-{d:%Y%m%d}.html"

    # Save HTML card (title + source only, matching the PIL card)
    html_content = _generate_express_html(headline, "", "", source, card)
    html_path.write_text(html_content, encoding="utf-8")

    # Clean import-ready HTML for Claude → Express (editable text layers).
    import_html_path = build_import_html(headline, source)

    post_path.write_text(fb_post, encoding="utf-8")
    md_path.write_text(_render_markdown(briefing, fb_post), encoding="utf-8")
    json_path.write_text(
        json.dumps(briefing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  → Saved {md_path.name}, {json_path.name}, {post_path.name}, {html_path.name}")

    _push_telegram(briefing, fb_post, briefing.get("express_url", ""))

    # Log the publication to Google Sheet (skipped if SHEET_WEBHOOK_URL unset).
    log_publication(briefing, card=card, express_url=briefing.get("express_url", ""))

    # Remember this story so later runs don't repost it.
    record_published(story.get("url", ""), story.get("headline_th", ""))

    return {
        "markdown": str(md_path),
        "json": str(json_path),
        "post": str(post_path),
        "card": card,
        "html_card": str(html_path),
        "import_html": import_html_path,
        "fb_post": fb_post,
    }


def publish_summary(express_url: str = "", chat: bool = True) -> str:
    """Re-send today's summary to Telegram as ONE message — card + ready-to-post
    caption + (optional) Adobe Express edit link. Use after importing the card
    to Express in-session so the team gets the post and the edit link together.
    Returns the combined message text."""
    d = date.today()
    jp = config.OUTPUT_DIR / f"briefing-{d:%Y%m%d}.json"
    briefing = json.loads(jp.read_text(encoding="utf-8"))
    if express_url:
        briefing["express_url"] = express_url
    fb_post = briefing.get("fb_post_final") or _build_fb_post(briefing)
    if chat:
        _push_telegram(briefing, fb_post, express_url)
    return fb_post


def _get_logo_data_uri() -> str:
    logo_path = config.LOGO_PATH
    if not logo_path.exists():
        logo_path = config.ASSETS_DIR / "logo_white.png"
    if not logo_path.exists():
        logo_path = config.ASSETS_DIR / "logo.svg"
    if not logo_path.exists():
        return ""
    try:
        if logo_path.suffix.lower() == ".svg":
            svg_data = logo_path.read_text(encoding="utf-8")
            svg_b64 = base64.b64encode(svg_data.encode("utf-8")).decode()
            return f"data:image/svg+xml;base64,{svg_b64}"
        else:
            from PIL import Image
            import io
            _logo_img = Image.open(logo_path).convert("RGBA")
            _logo_img.thumbnail((220, 220), Image.LANCZOS)
            _buf = io.BytesIO()
            _logo_img.save(_buf, "PNG", optimize=True)
            logo_b64 = base64.b64encode(_buf.getvalue()).decode()
            return f"data:image/png;base64,{logo_b64}"
    except Exception:
        return ""


def _generate_express_html(headline: str, subtitle: str, detail: str, source: str, png_card_path: str) -> str:
    from pathlib import Path
    
    logo_uri = _get_logo_data_uri()
    
    png_data_uri = ""
    try:
        p_path = Path(png_card_path)
        if p_path.exists():
            png_b64 = base64.b64encode(p_path.read_bytes()).decode()
            png_data_uri = f"data:image/png;base64,{png_b64}"
    except Exception:
        pass

    adobe_client_id = config.ADOBE_CLIENT_ID or ""

    logo_img_tag = f'<img class="logo" src="{logo_uri}" alt="CivicSpace Logo"/>' if logo_uri else ''
    source_div_tag = f'<div class="source-credit">ที่มา: {source}</div>' if source else ''

    # Using a raw multi-line string to avoid python f-string curly braces escaping issues entirely!
    html_template = """<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8" />
  <title>CivicSpace Card Editor — __HEADLINE__</title>
  <meta name="hz:slide-selector" content=".card" />
  <meta name="hz:canvas-width" content="1080" />
  <meta name="hz:canvas-height" content="1350" />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Kanit:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap" />
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
      background: #1e1e1e;
      color: #ffffff;
      font-family: "Kanit", sans-serif;
      padding-bottom: 50px;
    }
    
    /* Control panel for screen only */
    .control-panel {
      width: 100%;
      max-width: 1080px;
      background: #2a2a2a;
      border: 1px solid #3d3d3d;
      border-radius: 12px;
      padding: 24px;
      margin: 24px 0;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #3d3d3d;
      padding-bottom: 16px;
      margin-bottom: 16px;
    }
    .panel-title {
      font-size: 24px;
      font-weight: 700;
      color: #f0d21e;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .panel-subtitle {
      font-size: 14px;
      color: #bcc6d0;
      margin-top: 4px;
    }
    .express-btn {
      background: linear-gradient(135deg, #ff1493 0%, #eb1000 100%);
      color: white;
      border: none;
      padding: 14px 28px;
      border-radius: 30px;
      font-family: "Kanit", sans-serif;
      font-weight: 700;
      font-size: 18px;
      cursor: pointer;
      box-shadow: 0 6px 20px rgba(235,16,0,0.4);
      transition: all 0.3s ease;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      text-decoration: none;
    }
    .express-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(235,16,0,0.6);
    }
    .instructions {
      background: #1f1f1f;
      border-left: 4px solid #f0d21e;
      padding: 16px;
      border-radius: 0 8px 8px 0;
      margin-top: 16px;
    }
    .instructions h4 {
      color: #f0d21e;
      font-size: 16px;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .instructions ol {
      margin-left: 20px;
      font-size: 14px;
      line-height: 1.6;
      color: #bcc6d0;
    }
    
    /* Card layout */
    .card {
      position: relative;
      width: 1080px;
      height: 1350px;
      background: #111111;
      overflow: hidden;
      box-shadow: 0 15px 50px rgba(0,0,0,0.8);
      border: 1px solid #2e2e2e;
    }
    
    /* Bottom scrim so white text stays readable on any background */
    .scrim {
      position: absolute;
      left: 0; bottom: 0;
      width: 1080px; height: 600px;
      background: linear-gradient(to bottom,
        rgba(0,0,0,0) 0%,
        rgba(0,0,0,0.5) 40%,
        rgba(0,0,0,0.92) 100%);
      z-index: 1;
    }
    .logo {
      position: absolute;
      top: 52px; right: 48px;
      width: 150px;
      height: 150px;
      z-index: 2;
    }
    .text-container {
      position: absolute;
      left: 64px; bottom: 64px;
      width: 952px;
      z-index: 3;
    }
    .headline {
      font-weight: 900;
      font-size: 104px;
      line-height: 1.05;
      color: #ffffff;
      letter-spacing: -1.5px;
      text-shadow: 0 4px 15px rgba(0,0,0,0.6);
    }
    .subtitle {
      font-weight: 700;
      font-size: 58px;
      line-height: 1.1;
      color: #eef2f6;
      margin-top: 24px;
      text-shadow: 0 2px 8px rgba(0,0,0,0.5);
    }
    .detail {
      font-weight: 300;
      font-size: 40px;
      line-height: 1.2;
      color: #bcc6d0;
      margin-top: 18px;
      text-shadow: 0 2px 6px rgba(0,0,0,0.4);
    }
    .footer-row {
      display: flex;
      flex-direction: column;
      margin-top: 36px;
      border-top: 1px solid rgba(255,255,255,0.15);
      padding-top: 24px;
    }
    .source-credit {
      font-weight: 400;
      font-size: 32px;
      color: #9cb1c6;
      margin-bottom: 12px;
    }
    .brand {
      font-weight: 600;
      font-size: 34px;
      letter-spacing: 4px;
      color: #f0d21e;
    }
    
    /* Modal styles */
    .modal-overlay {
      display: none;
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.85);
      z-index: 10000;
      justify-content: center;
      align-items: center;
    }
    .modal {
      background: #2a2a2a;
      border: 1px solid #3d3d3d;
      border-radius: 16px;
      padding: 32px;
      max-width: 600px;
      width: 90%;
      box-shadow: 0 10px 40px rgba(0,0,0,0.6);
      position: relative;
    }
    .modal-close {
      position: absolute;
      top: 16px; right: 16px;
      background: none; border: none; color: #ccc;
      font-size: 24px; cursor: pointer;
    }
    .modal-close:hover { color: white; }
    
    /* Print optimizations */
    @media print {
      body {
        background: transparent !important;
        padding-bottom: 0 !important;
        display: block !important;
      }
      .control-panel, .modal-overlay, .modal {
        display: none !important;
      }
      .card {
        position: absolute;
        top: 0; left: 0;
        border: none !important;
        box-shadow: none !important;
        margin: 0 !important;
      }
    }
  </style>
</head>
<body>

  <!-- CONTROL PANEL (Screen Only) -->
  <div class="control-panel">
    <div class="panel-header">
      <div>
        <div class="panel-title">
          <span>🍺 CivicSpace Card Editor</span>
        </div>
        <div class="panel-subtitle">การ์ดสไตล์โมเดิร์นพาดหัวข่าวแอลกอฮอล์เพื่อประโยชน์สาธารณะ</div>
      </div>
      <div>
        <button id="edit-btn" class="express-btn">
          🎨 ส่งไปแก้ไขใน Adobe Express
        </button>
      </div>
    </div>
    
    <div style="font-size: 14px; line-height: 1.6; color: #eef2f6;">
      <span style="color: #f0d21e; font-weight: bold;">💡 ข้อมูลบนการ์ดใบนี้:</span><br/>
      • <b>พาดหัวหลัก:</b> __HEADLINE__<br/>
      • <b>คำโปรย/ประเภท:</b> __SUBTITLE__<br/>
      • <b>รายละเอียดบรรณาธิการ:</b> __DETAIL__<br/>
      • <b>แหล่งที่มาข่าว:</b> __SOURCE__
    </div>
    
    <div class="instructions">
      <h4>💡 วิธีนำการ์ดนี้ไปแก้ไขต่อบน Adobe Express อย่างมีประสิทธิภาพสูงสุด (100% Vector & Editable Texts)</h4>
      <ol>
        <li>กดคีย์ลัด <b>Cmd + P</b> (บน Mac) หรือ <b>Ctrl + P</b> (บน Windows) เพื่อสั่งพิมพ์หน้านี้</li>
        <li>เลือกจุดหมายปลายทางเป็น <b>"บันทึกเป็น PDF" (Save as PDF)</b></li>
        <li><b>สำคัญมาก:</b> เปิด "การตั้งค่าเพิ่มเติม" (More settings) แล้วติ๊กถูกที่ <b>"ซ่อนหัวกระดาษและท้ายกระดาษ"</b> (Hide headers and footers) และตรวจสอบให้แน่ใจว่าไม่มีกล่องสีเทาปุ่มควบคุมรบกวน</li>
        <li>เปิดเว็บไซต์ <b><a href="https://new.express.adobe.com/" target="_blank" style="color: #f0d21e; text-decoration: underline;">new.express.adobe.com</a></b> ในแถบใหม่</li>
        <li><b>ลากไฟล์ PDF ที่บันทึกไว้</b> มาปล่อยลงในหน้าเว็บ Adobe Express เพื่ออัปโหลด</li>
        <li>Adobe Express จะใช้พลัง AI แปลงโลโก้ เส้น และตัวหนังสือทั้งหมดเป็น<b>เลเยอร์แบบเวกเตอร์และกล่องข้อความที่คุณสามารถกดพิมพ์ใหม่ เปลี่ยนฟอนต์ ขยับสี หรือตกแต่งเพิ่มได้ทันที 100%!</b></li>
      </ol>
    </div>
  </div>

  <!-- THE ACTUAL CARD -->
  <div class="card" id="cs-card">
    <div class="scrim"></div>
    __LOGO_IMG_TAG__
    <div class="text-container">
      <div class="headline">__HEADLINE__</div>
      <div class="subtitle">__SUBTITLE__</div>
      <div class="detail">__DETAIL__</div>
      <div class="footer-row">
        __SOURCE_DIV_TAG__
        <div class="brand">CIVIC SPACE</div>
      </div>
    </div>
  </div>

  <!-- MODAL FOR SDK FALLBACK -->
  <div class="modal-overlay" id="modal-overlay">
    <div class="modal">
      <button class="modal-close" id="modal-close">&times;</button>
      <h3 style="color: #f0d21e; margin-bottom: 12px; font-size: 20px;">🎨 กำลังเปิด Adobe Express</h3>
      <p style="font-size: 15px; line-height: 1.6; color: #eef2f6; margin-bottom: 16px;">
        เราได้เปิดหน้าเว็บ Adobe Express ให้คุณแล้วในอีกแถบหนึ่งเพื่อใช้แก้ไขการ์ดนี้ต่ออย่างง่ายดาย!
      </p>
      <div style="background: #1f1f1f; padding: 16px; border-radius: 8px; font-size: 14px; color: #bcc6d0; line-height: 1.5;">
        <b style="color: #ffffff;">📌 แนะนำขั้นตอนการทำ:</b><br/>
        1. <b>บันทึกหน้านี้เป็น PDF:</b> กด <code style="background: #333; padding: 2px 6px; border-radius: 4px;">Cmd+P</code> หรือ <code style="background: #333; padding: 2px 6px; border-radius: 4px;">Ctrl+P</code> และกด "Save as PDF"<br/>
        2. <b>อัปโหลดเข้า Adobe Express:</b> นำไฟล์ PDF ไปลากวางที่เว็บ Adobe Express เพื่อแปลงเป็นโครงงานดีไซน์ที่<b>สามารถแก้ไขกล่องข้อความและเวกเตอร์ได้ 100%</b><br/>
        3. หรือหากต้องการทำงานรวดเร็ว สามารถดาวน์โหลดรูป <code style="background: #333; padding: 2px 6px; border-radius: 4px;">card-__DATE_TODAY__.png</code> เพื่อนำเข้าเป็นภาพหลังได้เช่นกัน
      </div>
      <button id="modal-ok" style="background: #f0d21e; color: black; border: none; padding: 10px 20px; border-radius: 6px; font-weight: bold; margin-top: 16px; width: 100%; cursor: pointer;">
        ตกลง และไปยัง Adobe Express
      </button>
    </div>
  </div>

  <!-- ADOBE EMBED SDK & FALLBACK SCRIPTS -->
  <script>
    const ADOBE_CLIENT_ID = "__ADOBE_CLIENT_ID__";
    const PNG_DATA_URI = "__PNG_DATA_URI__";
    const EXPRESS_URL = "https://new.express.adobe.com/";

    const editBtn = document.getElementById('edit-btn');
    const modalOverlay = document.getElementById('modal-overlay');
    const modalClose = document.getElementById('modal-close');
    const modalOk = document.getElementById('modal-ok');

    // SDK Init check
    let sdkInitialized = false;

    if (ADOBE_CLIENT_ID && ADOBE_CLIENT_ID.trim() !== "") {
      // Load Adobe SDK dynamically
      const script = document.createElement('script');
      script.src = "https://sdk.cc-embed.adobe.com/v3/CCEverywhere.js";
      script.onload = async () => {
        try {
          const ccEverywhere = await window.CCEverywhere.initialize({
            clientId: ADOBE_CLIENT_ID,
            appName: "CivicSpace Card Editor"
          });
          sdkInitialized = true;
          
          editBtn.addEventListener('click', () => {
            if (PNG_DATA_URI) {
              ccEverywhere.editor.createDesign({
                inputParams: {
                  asset: {
                    data: PNG_DATA_URI,
                    dataType: "base64",
                    type: "image"
                  }
                },
                exportConfig: [
                  {
                    id: "edit-in-express",
                    label: "Edit in Adobe Express",
                    action: { target: "express" },
                    style: { uiType: "button" }
                  }
                ]
              });
            } else {
              window.open(EXPRESS_URL, '_blank');
            }
          });
        } catch (e) {
          console.error("Failed to init Adobe SDK", e);
          setupFallback();
        }
      };
      script.onerror = () => setupFallback();
      document.head.appendChild(script);
    } else {
      setupFallback();
    }

    function setupFallback() {
      editBtn.addEventListener('click', (e) => {
        e.preventDefault();
        modalOverlay.style.display = 'flex';
      });
    }

    // Modal Close operations
    modalClose.addEventListener('click', () => {
      modalOverlay.style.display = 'none';
    });

    modalOk.addEventListener('click', () => {
      window.open(EXPRESS_URL, '_blank');
      modalOverlay.style.display = 'none';
    });

    // Close on overlay click
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) {
        modalOverlay.style.display = 'none';
      }
    });
  </script>
</body>
</html>
"""
    return html_template.replace("__HEADLINE__", headline) \
                         .replace("__SUBTITLE__", subtitle) \
                         .replace("__DETAIL__", detail) \
                         .replace("__SOURCE__", source) \
                         .replace("__LOGO_IMG_TAG__", logo_img_tag) \
                         .replace("__SOURCE_DIV_TAG__", source_div_tag) \
                         .replace("__ADOBE_CLIENT_ID__", adobe_client_id) \
                         .replace("__PNG_DATA_URI__", png_data_uri) \
                         .replace("__DATE_TODAY__", f"{date.today():%Y%m%d}")

