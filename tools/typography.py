"""Typography card — transparent PNG, logo + headline only (no AI image).

Style: CivicSpace transparent card
  - Fully transparent background (RGBA) + soft bottom gradient scrim
  - CivicSpace logo top-right (white)
  - Seppuri font, big→small tiers for an eye-catching headline
  - Gold "CIVIC SPACE" wordmark at the bottom
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config

CANVAS   = (1080, 1350)            # Instagram portrait 4:5
FONT_DIR = Path("/Users/sdnthailand/Library/Fonts")
_ASSET   = Path(__file__).parent.parent / "assets"

# Seppuri weights (a.k.a. "sappuri") — used for subtitle/detail/source/brand
_W = {
    "bold":     FONT_DIR / "Seppuri-Bold.otf",
    "semibold": FONT_DIR / "Seppuri-SemiBold.otf",
    "medium":   FONT_DIR / "Seppuri-Medium.otf",
    "regular":  FONT_DIR / "Seppuri-Regular.otf",
    "light":    FONT_DIR / "Seppuri-Light.otf",
    "thin":     FONT_DIR / "Seppuri-Thin.otf",
}

# Headline font — FC Vision (heavy weight for an eye-catching title)
_HEADLINE_FONT = FONT_DIR / "FCVision-Black.otf"

# Cross-platform Thai fallbacks so cards render on Linux (CI/VPS) too.
_LINUX_THAI_BOLD = [
    "/usr/share/fonts/truetype/tlwg/Sarabun-Bold.ttf",
    "/usr/share/fonts/truetype/tlwg/Waree-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf",
]
_LINUX_THAI = [
    "/usr/share/fonts/truetype/tlwg/Sarabun.ttf",
    "/usr/share/fonts/truetype/tlwg/Waree.ttf",
    "/usr/share/fonts/truetype/tlwg/Loma.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
]
_MAC_THAI = ["/System/Library/Fonts/Thonburi.ttc"]

WHITE  = (255, 255, 255)
OFF    = (236, 240, 244)
GREY   = (188, 198, 208)
GOLD   = (240, 210, 30)

MARGIN = 64


def _load(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    """Return the first loadable font from `paths`, else PIL's default."""
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _f(weight: str, size: int) -> ImageFont.FreeTypeFont:
    bold = weight in ("bold", "semibold", "medium")
    paths = [str(_W.get(weight, _W["regular"]))]
    paths += (_LINUX_THAI_BOLD if bold else _LINUX_THAI) + _LINUX_THAI + _MAC_THAI
    return _load(paths, size)


def _fhead(size: int) -> ImageFont.FreeTypeFont:
    """Headline font — FC Vision Black, with cross-platform Thai fallbacks."""
    return _load([str(_HEADLINE_FONT), str(_W["bold"])]
                 + _LINUX_THAI_BOLD + _MAC_THAI + _LINUX_THAI, size)


def _wrap(text: str, draw: ImageDraw.ImageDraw,
          font: ImageFont.FreeTypeFont, max_px: int) -> list[str]:
    """Wrap to max_px. Splits on spaces, then falls back to character-level
    breaking for long unbroken runs (Thai has no inter-word spaces)."""
    if not text or not text.strip():
        return []

    def width(s: str) -> float:
        return draw.textlength(s, font=font)

    words = text.split() if " " in text else [text]
    lines, cur = [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if width(trial) <= max_px:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = word
        # Single token still too wide → break by character.
        while width(cur) > max_px:
            lo, hi = 1, len(cur)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if width(cur[:mid]) <= max_px:
                    lo = mid
                else:
                    hi = mid - 1
            lines.append(cur[:lo])
            cur = cur[lo:]
    if cur:
        lines.append(cur)
    return lines


def _logo(size: int = 150) -> Image.Image | None:
    p = _ASSET / "logo_white.png"
    if not p.exists():
        return None
    img = Image.open(p).convert("RGBA")
    img.thumbnail((size, size), Image.LANCZOS)
    return img


def generate_typography_card(headline: str, subtitle: str = "",
                             detail: str = "", source: str = "",
                             index: int | None = None) -> str:
    """Render a transparent typography card: logo + headline tiers.

    headline → big bold, subtitle → medium semibold, detail → light grey.
    `source` renders a "ที่มา: …" credit line above the CIVIC SPACE wordmark.
    `index` (1-based) appends a suffix to the filename so several cards from
    the same day don't overwrite each other. Returns the output PNG path.
    """
    w, h = CANVAS
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    max_w = w - MARGIN * 2

    # ── Fonts: big → small for visual rhythm ──────────────────────────────────
    f_sub  = _f("semibold",  62)
    f_det  = _f("light",     44)
    f_tag  = _f("medium",    34)

    f_src  = _f("regular",   32)         # "ที่มา: …" credit line

    LH_SUB, LH_DET = 78, 58
    GAP_SUB, GAP_DET = 26, 18
    GAP_FOOTER = 36                      # gap between text and the credit/footer
    SOURCE_H   = 42                      # "ที่มา: …" row
    GAP_SOURCE = 10                      # gap between credit and CIVIC SPACE
    FOOTER_H   = 44                      # CIVIC SPACE wordmark row
    BOTTOM_MARGIN = 64                   # space below footer to image edge

    # ── Headline auto-fit: shrink until it fits in ≤3 lines with no orphan ────
    # (orphan = a final line of ≤2 characters, which looks broken).
    MAX_HEAD_LINES = 3
    head_size, head_lines = 72, []
    for head_size in (104, 96, 88, 80, 72, 64):
        f_head = _fhead(head_size)
        head_lines = _wrap(headline, draw, f_head, max_w)
        fits = len(head_lines) <= MAX_HEAD_LINES
        no_orphan = len(head_lines) <= 1 or len(head_lines[-1].strip()) > 2
        if fits and no_orphan:
            break
    head_lines = head_lines[:MAX_HEAD_LINES]
    LH_HEAD = int(head_size * 1.12)

    sub_lines  = _wrap(subtitle, draw, f_sub,  max_w)[:2]
    det_lines  = _wrap(detail,   draw, f_det,  max_w)[:2]
    source_txt = f"ที่มา: {source}".strip() if source else ""

    # ── Measure the text block bottom-up ──────────────────────────────────────
    head_h = len(head_lines) * LH_HEAD
    sub_h  = (GAP_SUB + len(sub_lines) * LH_SUB) if sub_lines else 0
    det_h  = (GAP_DET + len(det_lines) * LH_DET) if det_lines else 0
    src_h  = (SOURCE_H + GAP_SOURCE) if source_txt else 0
    block_h  = head_h + sub_h + det_h + GAP_FOOTER + src_h + FOOTER_H
    pad_top  = 70

    # Anchor the whole text+footer block to the bottom as one compact unit.
    text_top = h - BOTTOM_MARGIN - block_h

    # ── Soft gradient scrim so white text stays readable on any background ────
    grad_top = text_top - pad_top
    band_h   = h - grad_top
    grad     = Image.new("RGBA", (w, band_h), (0, 0, 0, 0))
    gd       = ImageDraw.Draw(grad)
    for y in range(band_h):
        alpha = int(205 * ((y / band_h) ** 0.45))
        gd.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    canvas.alpha_composite(grad, (0, grad_top))
    draw = ImageDraw.Draw(canvas)

    # ── Logo top-right ────────────────────────────────────────────────────────
    logo = _logo()
    if logo:
        lw, lh = logo.size
        canvas.alpha_composite(logo, (w - lw - 48, 52))
        draw = ImageDraw.Draw(canvas)

    # ── Headline (big bold) ───────────────────────────────────────────────────
    y = text_top
    for line in head_lines:
        draw.text((MARGIN + 2, y + 3), line, font=f_head, fill=(0, 0, 0, 130))
        draw.text((MARGIN,     y),     line, font=f_head, fill=(*WHITE, 255))
        y += LH_HEAD

    # ── Subtitle (medium) ─────────────────────────────────────────────────────
    if sub_lines:
        y += GAP_SUB
        for line in sub_lines:
            draw.text((MARGIN + 2, y + 2), line, font=f_sub, fill=(0, 0, 0, 110))
            draw.text((MARGIN,     y),     line, font=f_sub, fill=(*OFF, 245))
            y += LH_SUB

    # ── Detail (light grey) ───────────────────────────────────────────────────
    if det_lines:
        y += GAP_DET
        for line in det_lines:
            draw.text((MARGIN, y), line, font=f_det, fill=(*GREY, 225))
            y += LH_DET

    # ── Source credit (ที่มา: …) ──────────────────────────────────────────────
    y += GAP_FOOTER
    if source_txt:
        draw.text((MARGIN, y), source_txt, font=f_src, fill=(*GREY, 220))
        y += SOURCE_H + GAP_SOURCE

    # ── Footer: gold CIVIC SPACE wordmark ─────────────────────────────────────
    draw.text((MARGIN, y), "CIVIC SPACE", font=f_tag, fill=(*GOLD, 245))

    suffix = f"-{index}" if index is not None else ""
    out = config.OUTPUT_DIR / f"card-{date.today():%Y%m%d}{suffix}.png"
    canvas.save(out, "PNG")
    print(f"  → Typography card saved: {out}")
    return str(out)
