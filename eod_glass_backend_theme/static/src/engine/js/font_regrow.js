/** @odoo-module **/
// Core (v4.42): titles and fields use the bundled fonts. When they finish loading after a form is on screen, a text
// that now wraps to one more line (a long record name in the display face, on a phone) was cut in half: Odoo grows
// its text areas on input and when their own box resizes, not when the font changes. Regrow the ones whose text is
// clipped, never below their current height.
import { resizeTextArea } from "@web/core/utils/autoresize";

function regrow() {
    if (!document.body || !document.body.classList.contains("o_aic_theme")) {
        return;
    }
    for (const textarea of document.querySelectorAll(".o_form_view textarea")) {
        if (textarea.style.height && textarea.scrollHeight > textarea.clientHeight + 1) {
            resizeTextArea(textarea, { minimumHeight: textarea.offsetHeight });
        }
    }
}

if (document.fonts) {
    document.fonts.addEventListener("loadingdone", regrow);
    document.fonts.ready.then(regrow);
}
