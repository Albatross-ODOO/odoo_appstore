/** @odoo-module **/
// Graph view, bar charts with several series: pointing at one series (a bar or its legend entry) fades the others,
// so the series being read stands out; leaving restores them. Line charts (stacked areas are filled by a gradient
// that does not fade), pie charts and single-series charts are unchanged. Lazy bundle, like the graph view.
import { patch } from "@web/core/utils/patch";
import { GraphRenderer } from "@web/views/graph/graph_renderer";

const FADED = 0.18;

function fade(value) {
    const one = (c) => {
        if (typeof c !== "string") {
            return c;
        }
        const color = Chart.helpers.color(c);
        return color.valid ? color.alpha(color.rgb.a * FADED).rgbString() : c;
    };
    return Array.isArray(value) ? value.map(one) : one(value);
}

patch(GraphRenderer.prototype, {
    getChartConfig() {
        const config = super.getChartConfig(...arguments);
        if (config.type === "bar" && (config.data?.datasets?.length || 0) > 1) {
            const previous = config.options.onHover;
            config.options.onHover = (event, elements, chart) => {
                previous?.(event, elements, chart);
                this.aicFocusSeries(chart, elements.length ? elements[0].datasetIndex : null);
            };
        }
        return config;
    },
    onLegendHover(ev, legendItem) {
        super.onLegendHover(...arguments);
        const chart = this.chart.instance();
        if (this.model.metaData.mode === "bar" && legendItem?.datasetIndex !== undefined && chart?.data.datasets.length > 1) {
            this.aicFocusSeries(chart, legendItem.datasetIndex);
        }
    },
    onLegendLeave() {
        super.onLegendLeave(...arguments);
        this.aicFocusSeries(this.chart.instance(), null);
    },
    aicFocusSeries(chart, index) {
        if (!chart || (chart.$aicFocus ?? null) === index) {
            return;
        }
        chart.$aicFocus = index;
        chart.data.datasets.forEach((dataset, i) => {
            if (!dataset.$aicColors) {
                dataset.$aicColors = { backgroundColor: dataset.backgroundColor, borderColor: dataset.borderColor };
            }
            const faded = index !== null && i !== index;
            dataset.backgroundColor = faded ? fade(dataset.$aicColors.backgroundColor) : dataset.$aicColors.backgroundColor;
            dataset.borderColor = faded ? fade(dataset.$aicColors.borderColor) : dataset.$aicColors.borderColor;
        });
        // Chart.js caches resolved element options (config resolvers and each controller's data options): drop
        // both, or the bars keep their old colour while only the legend changes; "none" is a direct update that
        // leaves shared element options alone, "active" (Chart.js's hover transition) refreshes them
        chart.config.clearCache?.();
        for (let i = 0; i < chart.data.datasets.length; i++) {
            const controller = chart.getDatasetMeta(i).controller;
            if (controller && "_cachedDataOpts" in controller) {
                controller._cachedDataOpts = {};
            }
        }
        chart.update("active");
        if (index !== null && !chart.$aicLeave) {
            // Chart.js does not always report the pointer leaving the canvas: restore on mouseleave too
            chart.$aicLeave = () => this.aicFocusSeries(chart, null);
            chart.canvas.addEventListener("mouseleave", chart.$aicLeave);
        }
    },
});
