/** @odoo-module **/
// Phones: screens slide — a new screen comes in from the right, going back (the back arrow, a breadcrumb, the
// browser's or phone's Back) brings the previous one in from the left. Only the direction is decided here (a short
// body class); the motion is CSS (transitions.scss), skipped when the system asks for reduced motion.
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

const BACK = ".o_back_button, .o_breadcrumb .breadcrumb-item:not(.active) a, .o_aic_crumb_item";

export const aicTransitionsService = {
    start() {
        let timer;
        const back = () => {
            document.body.classList.add("o_aic_nav_back");
            browser.clearTimeout(timer);
            timer = browser.setTimeout(() => document.body.classList.remove("o_aic_nav_back"), 700);
        };
        browser.addEventListener("popstate", back);
        document.addEventListener("click", (ev) => ev.target.closest?.(BACK) && back(), true);
        // the first screen of a visit appears without sliding in
        browser.setTimeout(() => document.body.classList.add("o_aic_nav_ready"), 1500);
    },
};
registry.category("services").add("aic_transitions", aicTransitionsService);
