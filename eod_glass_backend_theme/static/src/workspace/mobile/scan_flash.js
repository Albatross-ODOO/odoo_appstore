/** @odoo-module **/
// Barcode app (Enterprise): every scan answers on the whole screen — a short green flash when it is taken, red when
// Odoo refuses it — so a storekeeper sees the result at arm's length, on top of Odoo's own sounds (when they are on).
// The Barcode screen is found in the actions registry at start-up: nothing here depends on the Barcode app.
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

function flash(kind) {
    const el = document.createElement("div");
    el.className = `o_aic_scan_flash o_${kind}`;
    el.setAttribute("aria-hidden", "true");
    document.body.appendChild(el);
    browser.setTimeout(() => el.remove(), 520);
}

export const aicScanFlashService = {
    start() {
        const Main = registry.category("actions").get("stock_barcode_client_action", null);
        if (!Main || Main.prototype.aicScanFlash) {
            return;
        }
        patch(Main.prototype, {
            aicScanFlash: true,
            setup() {
                super.setup(...arguments);
                if (this.env.model) {
                    useBus(this.env.model, "playSound", (ev) => flash(ev.detail === "error" ? "error" : "ok"));
                }
            },
        });
    },
};
registry.category("services").add("aic_scan_flash", aicScanFlashService);
