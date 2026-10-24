# -*- coding: utf-8 -*-
"""EOD colours: the Lagoon house palette, the two ready-made palettes, and the CSS a company palette
becomes on glass.

On glass the panes are translucent, so the roles a company may change are the colours only (action,
"you are here", ink, links, muted text) plus the three soft blobs of the colour field behind the panes.
Surfaces, wells, edges and shadows stay glass. Values match the EOD Suite design canvas.
"""
from odoo.addons.aic_theme.models import palette

# the effective colour of a light pane over the field (links and muted text are tuned against it)
GROUND_LIGHT = "#F2F5FA"
GROUND_DARK = "#2A2D36"      # a dark raised pane: links and muted text must read on it too

# the window behind the backend (installed app status bar, start-up screen): the field's ground
WINDOW_LIGHT = "#EEF2F8"
WINDOW_DARK = "#0A0C12"

# Lagoon "you are here": (hi, hi_ink, hi_soft, hi_soft_ink)
HOUSE_HIGHLIGHT = ("#D6E7FF", "#003C88", "#EAF3FF", "#00408F")


def _roles(light, dark):
    return {"light": light, "dark": dark, "custom": True}


# Lagoon as roles (the settings preview, documents); not custom: the stylesheet already holds it
LAGOON = {
    "light": {"act": "#0060D6", "act_ink": "#FFFFFF", "link": "#0060D6", "head": "#111318", "muted": "#5A606C",
              "well": "#EEF2F8", "hi": "#D6E7FF", "hi_ink": "#003C88", "hi_soft": "#EAF3FF", "hi_soft_ink": "#00408F",
              "plum": "#0060D6", "plum_muted": "#FFFFFF"},
    "dark": {"act": "#4C93FF", "act_ink": "#04122B", "link": "#7DB2FF", "head": "#FFFFFF", "muted": "#ADB3BE",
             "well": "#0A0C12", "surface": "#0A0C12", "surface_high": GROUND_DARK,
             "hi": "#1F3F73", "hi_ink": "#D6E7FF", "hi_soft": "rgba(76, 147, 255, 0.16)", "hi_soft_ink": "#BBD6FF",
             "plum": "#1C3D73", "plum_muted": "#C8DAF5"},
    "custom": False,
}

PRESETS = {
    "graphite": _roles(
        {"act": "#18181B", "act_ink": "#FFFFFF", "link": "#0B7A3B", "head": "#111318", "muted": "#5A606C",
         "well": "#F1F3F2", "hi": "#3DDC84", "hi_ink": "#05210F", "hi_soft": "#DDF7E8", "hi_soft_ink": "#0B5A2C",
         "plum": "#18181B", "plum_muted": "#C9CED8",
         "blobs": ("#CFF3DF", "#D3ECF7", "#E7E4F5")},
        {"act": "#F4F4F6", "act_ink": "#111113", "link": "#5BE39A", "head": "#FFFFFF", "muted": "#A3A9B5",
         "well": "#0A0C0B", "surface": "#0A0C0B", "surface_high": GROUND_DARK,
         "hi": "#3DDC84", "hi_ink": "#04170B", "hi_soft": "rgba(61, 220, 132, 0.16)", "hi_soft_ink": "#8FF0BA",
         "plum": "#2A2D36", "plum_muted": "#C9CED8",
         "blobs": ("#0E3A26", "#0C2D3C", "#1F1A36")}),
    "iris": _roles(
        {"act": "#4F46E5", "act_ink": "#FFFFFF", "link": "#4338CA", "head": "#111318", "muted": "#5A606C",
         "well": "#F2F1F8", "hi": "#FFE0C2", "hi_ink": "#7A3300", "hi_soft": "#FFF1E4", "hi_soft_ink": "#7A3300",
         "plum": "#1E1B4B", "plum_muted": "#CFCCF0",
         "blobs": ("#DEDAFF", "#D4E9FF", "#FFE6D3")},
        {"act": "#8B85FF", "act_ink": "#0B0A24", "link": "#A9A4FF", "head": "#FFFFFF", "muted": "#A3A9B5",
         "well": "#0B0B12", "surface": "#0B0B12", "surface_high": GROUND_DARK,
         "hi": "#5A3A1F", "hi_ink": "#FFD9B8", "hi_soft": "rgba(255, 184, 120, 0.14)", "hi_soft_ink": "#FFD9B8",
         "plum": "#2A2D36", "plum_muted": "#CFCCF0",
         "blobs": ("#251E62", "#0D2B4A", "#3D2414")}),
}


def field_blobs(roles, scheme):
    """Three soft tints for the colour field, from the action and "you are here" hues."""
    r = roles["dark" if scheme == "dark" else "light"]
    if r.get("blobs"):
        return r["blobs"]
    light = roles["light"]
    ah = palette.to_hsl(light["act"])[0]
    hh = palette.to_hsl(light["hi"])[0] if palette.is_hex(light["hi"]) else ah
    if scheme == "dark":
        return (palette.hsl(ah, 0.55, 0.22), palette.hsl(hh, 0.45, 0.20), palette.hsl(ah + 40, 0.40, 0.18))
    return (palette.hsl(ah, 0.85, 0.88), palette.hsl(hh, 0.75, 0.90), palette.hsl(ah + 40, 0.55, 0.91))


def glass_css(roles, scheme, tint=True, selector="body.o_aic_theme.o_aic_skin_eod"):
    """The company palette on glass: colour roles and the field's blobs; '' for the house palette."""
    if not roles.get("custom"):
        return ""
    dark = scheme == "dark"
    r = roles["dark" if dark else "light"]
    act_rgb = ", ".join(str(c) for c in palette.hex_to_rgb(r["act"]))
    hover = palette._lighten(r["act"], 0.06) if dark else palette._darken(r["act"], 0.06)
    decl = {
        "--nm-brand": r["act"],
        "--nm-brand-rgb": act_rgb,
        "--nm-brand-contrast": r["act_ink"],
        "--nm-brand-hover": hover,
        "--nm-brand-shadow": palette.rgba(r["act"], 0.45 if dark else 0.30),
        "--nm-action": r["link"],
        "--nm-action-hover": palette._lighten(r["link"], 0.08) if dark else palette._darken(r["link"], 0.1),
        "--nm-action-contrast": palette.WHITE if palette.contrast(r["link"], palette.WHITE) >= 4.5 else r["act_ink"],
        "--nm-action-shadow": palette.rgba(r["link"], 0.3),
        "--nm-current": r["hi"],
        "--nm-current-ink": r["hi_ink"],
        "--nm-active-tint": r["hi_soft"],
        "--nm-current-soft-ink": r["hi_soft_ink"],
        "--nm-ink": r["head"],
        # the one strong surface (Home's focus card) carries white text: the action colour when it reads
        # with white, else the ink; in dark mode a deep tone of the action hue
        "--nm-plum": (r["plum"] if dark      # derived palettes: a deep tone of the ink's hue; presets: their own
                      else r["act"] if palette.contrast(r["act"], palette.WHITE) >= 4.5 else r["head"]),
        "--nm-text-muted": r["muted"],
        "--nm-dot": palette.rgba(r["act"], 0.10),
    }
    if tint:
        a, b, c = field_blobs(roles, scheme)
        decl.update({"--gl-blob-a": a, "--gl-blob-b": b, "--gl-blob-c": c})
    return "%s { %s; }" % (selector, "; ".join("%s: %s" % kv for kv in decl.items()))
