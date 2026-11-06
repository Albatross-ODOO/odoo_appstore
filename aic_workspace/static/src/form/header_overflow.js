/** @odoo-module **/
// Desktop record header: past four buttons a header reads as a toolbar, and the main action is lost
// in it (a posted invoice has six). Above four, the header shows three: every primary button, then
// the next ones in the view's order, and the rest go under "⋯" (Odoo already does this on phones).
// Presentation only: the same buttons, the same order, the same actions.
import { FormCompiler } from "@web/views/form/form_compiler";
import { StatusBarButtons } from "@web/views/form/status_bar_buttons/status_bar_buttons";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

export const AIC_HEADER_MAX = 4; // up to this many buttons, all stay in the header
const SHOWN = 3; // above it, this many stay (primaries first in rank, view order kept)

patch(FormCompiler.prototype, {
    compileHeader(el, params) {
        const statusBar = super.compileHeader(el, params);
        const buttons = statusBar.querySelector("StatusBarButtons");
        for (const slot of buttons ? buttons.children : []) {
            const cls = (slot.firstElementChild && slot.firstElementChild.getAttribute("className")) || "";
            slot.setAttribute("aicPrimary", /\b(oe_highlight|btn-primary)\b/.test(cls) ? "true" : "false");
        }
        return statusBar;
    },
});

patch(StatusBarButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.aicPrefs = useService("aic_prefs");
    },
    // [shown, overflow] slot names for the desktop header; overflow is empty at four buttons or fewer
    // or when the user turned the compact header off (Core preferences)
    get aicHeaderSplit() {
        const names = this.visibleSlotNames;
        if (names.length <= AIC_HEADER_MAX || !this.aicPrefs.prefs.header_compact) {
            return [names, []];
        }
        const primary = new Set(names.filter((n) => this.props.slots[n].aicPrimary));
        const keep = new Set(primary);
        for (const n of names) {
            if (keep.size >= Math.max(SHOWN, primary.size)) {
                break;
            }
            keep.add(n);
        }
        return [names.filter((n) => keep.has(n)), names.filter((n) => !keep.has(n))];
    },
});
