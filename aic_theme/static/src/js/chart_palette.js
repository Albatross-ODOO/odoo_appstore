/** @odoo-module **/
// Core (phase 46): charts in the company's palette. Odoo's graph, pivot-to-graph and dashboard charts take their
// series colours from the shared palettes of @web/core/colors/colors (Chart.js blue, red, teal… by default). While
// the Core look is on (body.o_aic_theme), those palettes are refilled once per page: the first series in the
// company's brand colour, then a fixed set of companions chosen to stay apart from it and from each other, then
// lighter tints of the same order for charts with many series (chart text: graph_font.js, in the lazy bundle
// with the graph view). With the look off nothing is touched.
import { registry } from "@web/core/registry";
import { getColors } from "@web/core/colors/colors";

const COMPANIONS = {
    light: ["#5B3A70", "#2A9D8F", "#D08A1E", "#C8557A", "#4F74B0", "#8C8496"],
    dark: ["#B48CD0", "#3DC4B2", "#F0B54A", "#E77FA0", "#84A6DB", "#A8A0B2"],
};
const TINTS = [0, 0.38, 0.62, 0.2, 0.5]; // share of the ground mixed into each further round of the series

function rgbOf(cssColor) {
    const probe = document.createElement("span");
    probe.style.color = cssColor;
    document.body.appendChild(probe);
    const m = getComputedStyle(probe).color.match(/\d+(\.\d+)?/g) || [0, 0, 0];
    probe.remove();
    return m.slice(0, 3).map(Number);
}
const hex = (rgb) => "#" + rgb.map((v) => Math.round(v).toString(16).padStart(2, "0")).join("").toUpperCase();
const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);

// CIE L*a*b* distance (ΔE 1976): how different two colours look
function lab(rgb) {
    const lin = rgb.map((v) => {
        v /= 255;
        return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    });
    const xyz = [
        (lin[0] * 0.4124 + lin[1] * 0.3576 + lin[2] * 0.1805) / 0.95047,
        lin[0] * 0.2126 + lin[1] * 0.7152 + lin[2] * 0.0722,
        (lin[0] * 0.0193 + lin[1] * 0.1192 + lin[2] * 0.9505) / 1.08883,
    ].map((v) => (v > 0.008856 ? Math.cbrt(v) : 7.787 * v + 16 / 116));
    return [116 * xyz[1] - 16, 500 * (xyz[0] - xyz[1]), 200 * (xyz[1] - xyz[2])];
}
export function aicColorDistance(a, b) {
    const [la, lb] = [lab(a), lab(b)];
    return Math.hypot(la[0] - lb[0], la[1] - lb[1], la[2] - lb[2]);
}
const MIN_DISTANCE = 20; // a companion closer than this to the company's colour would read as the same series

export function aicChartColors(n, scheme, brandColor) {
    const css = getComputedStyle(document.body);
    const brand = rgbOf(brandColor || css.getPropertyValue("--nm-brand").trim() || "#FF6A2B");
    const ground = rgbOf(css.getPropertyValue("--nm-surface").trim() || "#FFFFFF");
    // a custom company colour can sit close to one of the fixed companions: that companion is left out (further
    // series take the lighter tints), so no two series read alike
    const bases = [brand, ...COMPANIONS[scheme].map(rgbOf).filter((c) => aicColorDistance(c, brand) >= MIN_DISTANCE)];
    const out = [];
    for (let i = 0; i < n; i++) {
        const round = Math.floor(i / bases.length);
        out.push(hex(mix(bases[i % bases.length], ground, TINTS[round % TINTS.length])));
    }
    return out;
}

const aicChartPaletteService = {
    start() {
        if (!document.body.classList.contains("o_aic_theme")) {
            return;
        }
        // one bundle per page: the dark bundle defines the dark tokens, so both lists take the page's scheme
        // (Odoo's color_scheme cookie first: the service can start before the stylesheet applies, when the surface
        // token still reads empty and a light page was taken for dark)
        const surface = getComputedStyle(document.body).getPropertyValue("--nm-surface").trim().toUpperCase();
        const scheme = document.documentElement.dataset.colorScheme === "dark" ||
            /(^|;\s*)color_scheme=dark/.test(document.cookie) || (surface && surface !== "#FFFFFF")
            ? "dark" : "light";
        // the same series colours as CSS variables, for views that colour their marks outside Chart.js (map pins)
        aicChartColors(10, scheme).forEach((color, i) => document.body.style.setProperty(`--aic-series-${i}`, color));
        for (const size of ["odoo", "sm", "md", "lg", "xl"]) {
            for (const s of ["light", "dark"]) {
                const palette = getColors(s, size);
                palette.splice(0, palette.length, ...aicChartColors(palette.length, scheme));
            }
        }
    },
};
registry.category("services").add("aic_chart_palette", aicChartPaletteService);
