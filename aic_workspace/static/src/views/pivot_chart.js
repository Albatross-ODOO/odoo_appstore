/** @odoo-module **/
// Phones: a pivot table is wide and scrolls sideways; when the action also has a chart view, the pivot's key row
// offers Chart, which switches to it with the same filters and measure. Lazy bundle (pivot lives there).
import { patch } from "@web/core/utils/patch";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";

patch(PivotRenderer.prototype, {
    get aicCanChart() {
        const views = (this.env.config && this.env.config.views) || [];
        return Boolean(this.uiService.isSmall) && views.some((v) => v[1] === "graph");
    },
    aicShowChart() {
        this.actionService.switchView("graph");
    },
});
