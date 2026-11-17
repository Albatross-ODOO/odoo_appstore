/** @odoo-module **/
// Gantt legend: Odoo marks pills with a coloured corner from the view's decoration-* rules (a planning overlap, a
// passed deadline, a refused leave…) but never says what the colours mean. Above the timeline, a key names each
// marker that appears on a shown pill, read from the rule itself: a boolean field gives its label ("Planning
// overlap"), a date compared with today gives "Deadline passed", a selection test gives the state names. A rule
// that cannot be put into words simply gets no key. Desktop renderer only (the phone gantt has its own view).
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { GanttRenderer } from "@web_gantt/gantt_renderer";

const ORDER = ["decoration-danger", "decoration-warning", "decoration-info", "decoration-success", "decoration-secondary"];

function selectionLabels(field, values) {
    const labels = Object.fromEntries(field.selection || []);
    return values.map((v) => labels[v] || v).join(", ");
}

export function aicDescribeDecoration(expr, fields) {
    const text = String(expr || "").trim();
    let m = text.match(/^(not\s+)?(\w+)$/);
    if (m && fields[m[2]]?.type === "boolean") {
        return m[1] ? _t("Not %(label)s", { label: fields[m[2]].string }) : fields[m[2]].string;
    }
    m = text.match(/^(\w+)\s*<=?\s*(current_date|today|now)\b/);
    if (m && ["date", "datetime"].includes(fields[m[1]]?.type)) {
        return _t("%(field)s passed", { field: fields[m[1]].string });
    }
    m = text.match(/^(\w+)\s*==\s*['"]([^'"]+)['"]$/);
    if (m && fields[m[1]]?.type === "selection") {
        return selectionLabels(fields[m[1]], [m[2]]);
    }
    m = text.match(/^(\w+)\s+in\s+[[(]([^\])]+)[\])]$/);
    if (m && fields[m[1]]?.type === "selection") {
        const values = [...m[2].matchAll(/['"]([^'"]+)['"]/g)].map((x) => x[1]);
        return values.length ? selectionLabels(fields[m[1]], values) : null;
    }
    return null;
}

patch(GanttRenderer.prototype, {
    get aicLegend() {
        const { pillDecorations, fields } = this.model.metaData;
        if (!pillDecorations) {
            return [];
        }
        const shown = new Set();
        for (const pill of Object.values(this.pills || {})) {
            for (const cls of (pill.className || "").split(" ")) {
                shown.add(cls);
            }
        }
        const keys = [];
        for (const decoration of ORDER) {
            if (!(decoration in pillDecorations) || !shown.has(decoration)) {
                continue;
            }
            const label = aicDescribeDecoration(pillDecorations[decoration], fields);
            if (label) {
                keys.push({ decoration, label });
            }
        }
        return keys;
    },
});
