#!/usr/bin/env python3
"""Build a self-contained HTML version of the CivicSpace typography card
for import into Adobe Express. Embeds the white logo as a base64 data URI.
"""
import base64
import io
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets" / "logo_white.png"

# Downscale the logo to keep the embedded data URI small (display size is 150px).
_logo_img = Image.open(LOGO).convert("RGBA")
_logo_img.thumbnail((220, 220), Image.LANCZOS)
_buf = io.BytesIO()
_logo_img.save(_buf, "PNG", optimize=True)
logo_b64 = base64.b64encode(_buf.getvalue()).decode()
logo_uri = f"data:image/png;base64,{logo_b64}"

# Editorial content (same tiers as the PIL card)
HEADLINE = "แอลกอฮอล์กับสุขภาพ"
SUBTITLE = "งานวิจัยเผย"
DETAIL   = "ลด–เลิกดื่มช่วยฟื้นฟูได้"

HTML = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8" />
  <title>CivicSpace Alcohol Briefing Card</title>
  <meta name="hz:slide-selector" content=".card" />
  <meta name="hz:canvas-width" content="1080" />
  <meta name="hz:canvas-height" content="1350" />
  <link rel="stylesheet" href="https://use.typekit.net/srp1ays.css" />
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      display: flex; justify-content: center; align-items: center;
      min-height: 100vh; background: #cfcfcf;
    }}
    .card {{
      position: relative;
      width: 1080px;
      height: 1350px;
      background: transparent;
      overflow: hidden;
      font-family: "kanit", sans-serif;
    }}
    /* Bottom scrim so white text stays readable on any background */
    .scrim {{
      position: absolute;
      left: 0; bottom: 0;
      width: 1080px; height: 560px;
      background: linear-gradient(to bottom,
        rgba(0,0,0,0) 0%,
        rgba(0,0,0,0.45) 45%,
        rgba(0,0,0,0.82) 100%);
    }}
    .logo {{
      position: absolute;
      top: 52px; right: 48px;
      width: 150px; height: 150px;
    }}
    .text {{
      position: absolute;
      left: 64px; bottom: 56px;
      width: 952px;
    }}
    .headline {{
      font-family: "kanit", sans-serif;
      font-weight: 900;
      font-size: 104px;
      line-height: 1.05;
      color: #ffffff;
      letter-spacing: -1px;
      text-shadow: 0 3px 12px rgba(0,0,0,0.45);
    }}
    .subtitle {{
      font-family: "kanit", sans-serif;
      font-weight: 700;
      font-size: 62px;
      line-height: 1.1;
      color: #eef2f6;
      margin-top: 22px;
      text-shadow: 0 2px 8px rgba(0,0,0,0.4);
    }}
    .detail {{
      font-family: "kanit", sans-serif;
      font-weight: 300;
      font-size: 44px;
      line-height: 1.15;
      color: #bcc6d0;
      margin-top: 16px;
    }}
    .brand {{
      font-family: "kanit", sans-serif;
      font-weight: 500;
      font-size: 34px;
      letter-spacing: 4px;
      color: #f0d21e;
      margin-top: 34px;
    }}
  </style>
</head>
<body>
  <div class="card" data-canvas-width="1080" data-canvas-height="1350">
    <div class="scrim"></div>
    <img class="logo" src="{logo_uri}" width="150" height="150" alt="CivicSpace logo" />
    <div class="text">
      <div class="headline">{HEADLINE}</div>
      <div class="subtitle">{SUBTITLE}</div>
      <div class="detail">{DETAIL}</div>
      <div class="brand">CIVIC SPACE</div>
    </div>
  </div>
</body>
</html>
"""

out = ROOT / "output" / "card-express.html"
out.write_text(HTML, encoding="utf-8")
print(out)
