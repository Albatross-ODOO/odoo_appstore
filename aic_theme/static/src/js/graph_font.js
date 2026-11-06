/** @odoo-module **/
// Core (phase 46): chart text in the interface font and the muted ink while the look is on. The graph view lives in
// Odoo's lazy bundle (web.assets_backend_lazy), so this patch ships there; the palette is chart_palette.js.
import { patch } from "@web/core/utils/patch";
import { GraphRenderer } from "@web/views/graph/graph_renderer";

patch(GraphRenderer.prototype, {
    prepareOptions() {
        const options = super.prepareOptions(...arguments);
        if (document.body.classList.contains("o_aic_theme") && window.Chart) {
            const css = getComputedStyle(document.body);
            window.Chart.defaults.font.family = css.fontFamily;
            window.Chart.defaults.color = css.getPropertyValue("--nm-text-muted").trim() || window.Chart.defaults.color;
        }
        return options;
    },
});
