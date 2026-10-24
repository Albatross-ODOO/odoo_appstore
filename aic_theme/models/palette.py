# -*- coding: utf-8 -*-
"""Core palette engine: turn a few brand colours into contrast-checked theme roles.

Pure Python, no Odoo imports, so it can be unit-tested on its own. Three inputs are possible:

* the house palette (no input): tangerine action, butter highlight, plum ink;
* the colours found in a company logo (``extract_logo_colors``);
* colours an administrator typed in (custom mode).

``derive_roles`` gives every colour one job (action, "you are here" highlight, ink) and then
nudges each role lighter or darker until its text reaches WCAG AA (4.5:1) against the ground it
sits on, separately for the light and the dark scheme. ``palette_css`` turns the roles into the
CSS custom properties the stylesheet reads (tokens.scss holds the same names with the house
values, so a company on the house palette needs no override at all).
"""
import colorsys
import math
import re

WHITE = "#FFFFFF"

HOUSE = {
    "action": "#FF6A2B",     # tangerine: buttons and the main action
    "highlight": "#FFE47A",  # butter: "you are here" (current stage, active app, selected row)
    "ink": "#2A1633",        # plum: headings, totals, the action dock
}


# --------------------------------------------------------------------------- colour maths
def hex_to_rgb(value):
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#" + "".join("%02X" % max(0, min(255, round(c))) for c in rgb)


def to_hsl(value):
    r, g, b = (c / 255 for c in hex_to_rgb(value))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s, l


def hsl(h, s, l):
    s = max(0.0, min(1.0, s))
    l = max(0.0, min(1.0, l))
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, l, s)
    return rgb_to_hex((r * 255, g * 255, b * 255))


def luminance(value):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in hex_to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def shift_to_contrast(value, against, target, direction):
    """Move ``value`` lighter (direction=1) or darker (-1) until it reaches ``target`` against ``against``."""
    h, s, l = to_hsl(value)
    out = value
    for _ in range(100):
        if contrast(out, against) >= target:
            break
        l += direction * 0.01
        out = hsl(h, s, l)
    return out


def rgba(value, alpha):
    r, g, b = hex_to_rgb(value)
    return "rgba(%d, %d, %d, %s)" % (r, g, b, ("%.3f" % alpha).rstrip("0").rstrip("."))


def is_hex(value):
    if not value or not isinstance(value, str):
        return False
    v = value.strip().lstrip("#")
    return len(v) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in v)


# --------------------------------------------------------------------------- logo colours
def _is_background(r, g, b):
    h, s, l = to_hsl(rgb_to_hex((r, g, b)))
    return l > 0.95 or (l > 0.88 and s < 0.15)


def _cluster_colors(samples, max_colors=5):
    """Group ``(r, g, b, weight)`` samples into the main colours: ``[(hex, share), ...]`` sorted by share.
    White/near-white (the logo's background) is ignored; groups under 3 % are dropped."""
    clusters = []   # [r_sum, g_sum, b_sum, weight]
    total = 0
    for r, g, b, w in samples:
        if w <= 0 or _is_background(r, g, b):
            continue
        total += w
        for k in clusters:
            n = k[3]
            if math.dist((k[0] / n, k[1] / n, k[2] / n), (r, g, b)) < 52:
                k[0] += r * w; k[1] += g * w; k[2] += b * w; k[3] += w
                break
        else:
            clusters.append([r * w, g * w, b * w, w])
    if not total:
        return []
    clusters.sort(key=lambda k: -k[3])
    out = []
    for r, g, b, n in clusters:
        share = n / total
        if share < 0.03:
            continue
        out.append((rgb_to_hex((r / n, g / n, b / n)), share))
        if len(out) >= max_colors:
            break
    return out


def extract_logo_colors(image, size=72, max_colors=5):
    """Group a logo's pixels into its main colours.

    ``image`` is a PIL image. Transparent pixels and the white/near-white background are
    ignored. Returns ``[(hex, share), ...]`` sorted by share, shares summing to about 1.
    """
    img = image.convert("RGBA")
    img.thumbnail((size, size))
    # Pillow 12 deprecates getdata() (removed in 14); get_flattened_data() is the same pixel sequence
    pixels = img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata()
    return _cluster_colors(((r, g, b, 1) for r, g, b, a in pixels if a >= 128), max_colors=max_colors)


# SVG logos: Pillow cannot read them and no rasteriser can be assumed on a server, so the colours are read
# from the markup: every filled shape counts with its area (shoelace over the path's end points, which is
# close enough for weighting; curves' control points are ignored, transforms too).
_SVG_TAG = re.compile(r"<(/?)([A-Za-z][\w:.-]*)((?:\"[^\"]*\"|'[^']*'|[^'\">])*?)(/?)>")
_SVG_NUM = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_SVG_ARGS = {"m": 2, "l": 2, "h": 1, "v": 1, "c": 6, "s": 4, "q": 4, "t": 2, "a": 7, "z": 0}
_SVG_HIDDEN = {"defs", "clippath", "mask", "pattern", "symbol", "lineargradient", "radialgradient", "filter",
               "metadata", "title", "desc", "style", "marker"}


def _svg_attr(attrs, name):
    """An SVG presentation value: the ``style`` declaration wins over the attribute, as in CSS."""
    style = re.search(r"(?:^|\s)style\s*=\s*([\"'])(.*?)\1", attrs)
    m = style and re.search(r"(?:^|;)\s*%s\s*:\s*([^;]+)" % name, style.group(2))
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:^|\s)%s\s*=\s*([\"'])(.*?)\1" % name, attrs)
    return m.group(2).strip() if m else None


def _svg_color(value):
    """``(r, g, b)`` of a #rgb, #rrggbb or rgb() paint, else None (none, gradients, currentColor, names)."""
    value = (value or "").strip().lower()
    if is_hex(value) and value.startswith("#"):
        return hex_to_rgb(value)
    m = re.match(r"rgb\(\s*([\d.]+%?)\s*,\s*([\d.]+%?)\s*,\s*([\d.]+%?)\s*\)", value)
    if m:
        return tuple(round(float(v[:-1]) * 2.55) if v.endswith("%") else round(float(v)) for v in m.groups())
    return {"black": (0, 0, 0), "white": (255, 255, 255)}.get(value)


def _svg_path_area(d):
    tokens = _SVG_NUM.findall(d or "")
    area, i, cmd = 0.0, 0, None
    x = y = sx = sy = 0.0
    poly = []

    def close():
        return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1])) if len(poly) > 2 else 0.0

    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                area += close()
                poly, x, y = [], sx, sy
                continue
        if cmd is None:
            break
        n = _SVG_ARGS[cmd.lower()]
        args = tokens[i:i + n]
        if len(args) < n or any(a.isalpha() for a in args):
            break
        i += n
        v = [float(a) for a in args]
        rel = cmd.islower()
        if cmd in "Hh":
            x = x + v[0] if rel else v[0]
        elif cmd in "Vv":
            y = y + v[0] if rel else v[0]
        else:
            x, y = (x + v[-2], y + v[-1]) if rel else (v[-2], v[-1])
        if cmd in "Mm":
            area += close()
            poly, sx, sy = [], x, y
            cmd = "l" if rel else "L"      # further pairs after a move are lines
        poly.append((x, y))
    return abs(area + close())


def _svg_shape_area(tag, attrs):
    def num(name):
        try:
            return float(re.sub(r"[a-z%]+$", "", _svg_attr(attrs, name) or "0"))
        except ValueError:
            return 0.0
    if tag == "rect":
        return num("width") * num("height")
    if tag == "circle":
        return math.pi * num("r") ** 2
    if tag == "ellipse":
        return math.pi * num("rx") * num("ry")
    if tag in ("polygon", "polyline"):
        pts = [float(v) for v in _SVG_NUM.findall(_svg_attr(attrs, "points") or "") if not v.isalpha()]
        return _svg_path_area("M" + " ".join(map(str, pts)) + "Z")
    if tag == "path":
        return _svg_path_area(_svg_attr(attrs, "d"))
    return 0.0


def extract_svg_colors(data, max_colors=5):
    """The main colours of an SVG logo (bytes or str), as ``extract_logo_colors`` gives them for a bitmap.
    Fills are inherited from groups; hidden definitions (defs, masks, gradients...) are skipped."""
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    samples, stack, hidden = [], [], 0
    for m in _SVG_TAG.finditer(text):
        closing, tag, attrs, selfclose = m.group(1), m.group(2).lower().split(":")[-1], m.group(3), m.group(4)
        if tag.startswith(("?", "!")):
            continue
        if closing:
            if stack:
                _tag, _fill, was_hidden = stack.pop()
                hidden -= was_hidden
            continue
        own = _svg_attr(attrs, "fill")
        fill = own if own is not None else (stack[-1][1] if stack else "#000000")
        is_hidden = tag in _SVG_HIDDEN
        if not hidden and not is_hidden and tag in ("path", "rect", "circle", "ellipse", "polygon", "polyline"):
            rgb = _svg_color(fill)
            area = _svg_shape_area(tag, attrs) if rgb else 0.0
            if rgb and area > 0:
                samples.append((*rgb, area))
        if not selfclose and not attrs.rstrip().endswith("/"):
            stack.append((tag, fill, int(is_hidden)))
            hidden += int(is_hidden)
    samples.sort(key=lambda s: -s[3])     # big shapes seed the groups
    return _cluster_colors(samples, max_colors=max_colors)


def svg_embedded_images(data, limit=3):
    """Bitmaps embedded in an SVG as data: URIs (a traced or wrapped raster logo), largest first."""
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    found = re.findall(r"data:image/(?:png|jpe?g|gif|webp);base64,([A-Za-z0-9+/=\s]+)", text)
    return sorted(found, key=len, reverse=True)[:limit]


def is_svg(data):
    head = (data[:2048] if isinstance(data, bytes) else data[:2048].encode()).lstrip().lower()
    return head.startswith(b"<svg") or (head.startswith((b"<?xml", b"<!--", b"<!doctype")) and b"<svg" in head)


# --------------------------------------------------------------------------- roles
def _hue_distance(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _pick(colors):
    """From ``[(hex, share)]`` pick (primary accent, secondary accent, dark ink)."""
    items = [dict(hex=c, share=sh, **dict(zip(("h", "s", "l"), to_hsl(c)))) for c, sh in colors if is_hex(c)]
    accents = sorted(
        (c for c in items if c["s"] >= 0.3 and 0.25 <= c["l"] <= 0.82),
        key=lambda c: -(c["share"] * (0.4 + c["s"])),
    )
    darks = sorted((c for c in items if c["l"] < 0.3), key=lambda c: -c["share"])
    primary = accents[0] if accents else None
    secondary = None
    if primary:
        secondary = next((c for c in accents[1:] if _hue_distance(c["h"], primary["h"]) >= 25), None)
    return primary, secondary, (darks[0] if darks else None)


def derive_roles(action=None, highlight=None, ink=None, colors=None, keep_house_highlight=False,
                 house_highlight=None, ground=WHITE):
    """Return ``{"light": {...}, "dark": {...}}`` role colours.

    Either pass explicit ``action`` / ``highlight`` / ``ink`` (custom mode; any may be empty), or
    ``colors`` from :func:`extract_logo_colors` (logo mode). With nothing at all, the result is
    the house palette.

    A look whose panes are not plain white passes its effective pane colour as ``ground`` (links and
    muted text are tuned against it) and its own "you are here" colours as ``house_highlight``
    (hi, hi_ink, hi_soft, hi_soft_ink), used when the highlight is kept or not given.
    """
    primary = secondary = dark = None
    if colors:
        p, s, d = _pick(colors)
        primary = p and p["hex"]
        secondary = s and s["hex"]
        dark = d and d["hex"]
    action = action if is_hex(action) else primary
    highlight = highlight if is_hex(highlight) else secondary
    ink = ink if is_hex(ink) else dark

    # --- action: the brand colour as a fill, with whichever text colour reads on it
    act, act_ink = HOUSE["action"], "#1E1410"
    if action:
        h, s, l = to_hsl(action)
        act = hsl(h, max(s, 0.55), l)
        dark_ink = hsl(h, 0.5, 0.1)
        if contrast(act, WHITE) >= 4.5:
            act_ink = WHITE
        elif l >= 0.5 and contrast(act, dark_ink) >= 4.5:
            act_ink = dark_ink
        else:
            act = shift_to_contrast(act, WHITE, 4.5, -1)
            act_ink = WHITE

    # --- ink: headings, totals bar, dock
    if ink:
        head = shift_to_contrast(ink, WHITE, 12, -1)
    elif action:
        head = hsl(to_hsl(act)[0], 0.45, 0.15)
    else:
        head = HOUSE["ink"]
    ih, isat, _il = to_hsl(head)

    # --- highlight ("you are here")
    hi, hi_ink, hi_soft, hi_soft_ink = house_highlight or (HOUSE["highlight"], "#3D3000", "#FFF6CC", "#5C4A00")
    if not keep_house_highlight and (highlight or action):
        src = highlight or act
        hh, hs, _hl = to_hsl(src)
        hi_ink = hsl(hh, 0.7, 0.13)
        hi = shift_to_contrast(hsl(hh, max(0.7, hs), 0.74 if highlight else 0.82), hi_ink, 7, 1)
        hi_soft = hsl(hh, 0.85, 0.94)
        hi_soft_ink = shift_to_contrast(hsl(hh, 0.75, 0.3), hi_soft, 4.5, -1)

    custom = bool(action or ink or (highlight and not keep_house_highlight))
    muted = shift_to_contrast(hsl(ih, min(isat, 0.18), 0.4), ground, 4.6, -1) if custom else "#5B4E46"
    link = shift_to_contrast(act, ground, 4.5, -1) if action else "#C2410C"
    well = hsl(ih, 0.22, 0.965) if custom else "#F6F5F8"

    light = {
        "act": act, "act_ink": act_ink, "link": link, "head": head, "muted": muted, "well": well,
        "hi": hi, "hi_ink": hi_ink, "hi_soft": hi_soft, "hi_soft_ink": hi_soft_ink,
        "plum": head, "plum_muted": hsl(ih, 0.25, 0.84) if custom else "#D9CBE3",
    }

    # --- dark scheme: same hues, lifted onto a plum-black ground
    pane = hsl(ih, 0.16, 0.10) if custom else "#1A1720"
    card = hsl(ih, 0.14, 0.14) if custom else "#221E29"
    ah, asat, al = to_hsl(act)
    if action:
        act_d = shift_to_contrast(hsl(ah, max(asat, 0.6), max(al, 0.58)), card, 3, 1)
        # links and muted text sit on panels AND on the lighter cards: tune against the card
        link_d = shift_to_contrast(hsl(ah, max(asat, 0.6), 0.6), card, 4.5, 1)
    else:
        act_d, link_d = "#FF7A3D", "#FF9A6B"
    act_d_ink = WHITE if contrast(act_d, WHITE) >= 4.5 else hsl(ah, 0.6, 0.08)
    dark_ = {
        "act": act_d, "act_ink": act_d_ink, "link": link_d,
        "head": "#FFFFFF",
        "muted": shift_to_contrast(hsl(ih, 0.12, 0.66), card, 4.6, 1) if custom else "#B8AEC2",
        "well": hsl(ih, 0.2, 0.06) if custom else "#0F0D13",
        "surface": hsl(ih, 0.15, 0.085) if custom else "#17141C",
        "surface_high": card,
        "hi": hi, "hi_ink": hi_ink, "hi_soft": rgba(hi, 0.12), "hi_soft_ink": shift_to_contrast(hi, card, 7, 1),
        "plum": hsl(ih, 0.28, 0.2) if custom else "#33263F",
        "plum_muted": hsl(ih, 0.2, 0.8) if custom else "#CDBEDA",
    }
    return {"light": light, "dark": dark_, "custom": custom}


# --------------------------------------------------------------------------- CSS
def _darken(value, amount):
    h, s, l = to_hsl(value)
    return hsl(h, s, l - amount)


def _lighten(value, amount):
    h, s, l = to_hsl(value)
    return hsl(h, s, l + amount)


def palette_css(roles, scheme="light", selector="body.o_aic_theme"):
    """CSS overriding tokens.scss for one scheme. Empty string for the house palette."""
    if not roles.get("custom"):
        return ""
    r = roles["dark" if scheme == "dark" else "light"]
    dark = scheme == "dark"
    act_rgb = ", ".join(str(c) for c in hex_to_rgb(r["act"]))
    decl = {
        # primary fill (btn-primary, Bootstrap primary utilities)
        "--nm-brand": r["act"],
        "--nm-brand-rgb": act_rgb,
        "--nm-brand-contrast": r["act_ink"],
        "--nm-brand-hover": _lighten(r["act"], 0.06) if dark else _darken(r["act"], 0.06),
        "--nm-brand-shadow": rgba(r["act"], 0.45 if dark else 0.32),
        # text-safe accent (links, active labels, focus rings, small fills with their contrast ink)
        "--nm-action": r["link"],
        "--nm-action-hover": _lighten(r["link"], 0.08) if dark else _darken(r["link"], 0.1),
        "--nm-action-contrast": WHITE if contrast(r["link"], WHITE) >= 4.5 else r["act_ink"],
        "--nm-action-shadow": rgba(r["link"], 0.3),
        # "you are here"
        "--nm-current": r["hi"],
        "--nm-current-ink": r["hi_ink"],
        "--nm-active-tint": r["hi_soft"],
        "--nm-current-soft-ink": r["hi_soft_ink"],
        # inks and grounds
        "--nm-ink": r["head"],
        "--nm-plum": r["plum"],
        "--nm-plum-muted": r["plum_muted"],
        "--nm-text-muted": r["muted"],
        "--nm-well-bg": r["well"],
        "--nm-dot": rgba(r["act"], 0.10),
        "--nm-glow-brand": rgba(r["act"], 0.05 if dark else 0.07),
        "--nm-glow-action": rgba(r["link"], 0.05 if dark else 0.07),
    }
    if dark:
        decl["--nm-surface"] = r["surface"]
        decl["--nm-surface-high"] = r["surface_high"]
    else:
        # shadows and hairlines take the ink's hue on a light ground
        decl["--nm-shadow-dark"] = rgba(r["head"], 0.14)
        decl["--nm-shadow-soft"] = rgba(r["head"], 0.06)
        decl["--nm-shadow-deep"] = rgba(r["head"], 0.22)
        decl["--nm-inset-dark"] = rgba(r["head"], 0.10)
        decl["--nm-edge"] = rgba(r["head"], 0.04)
        decl["--nm-hairline"] = rgba(r["head"], 0.10)
    body = "; ".join("%s: %s" % kv for kv in decl.items())
    return "%s { %s; }" % (selector, body)
