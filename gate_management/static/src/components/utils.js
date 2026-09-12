/** @odoo-module */

const FONT_URL = "https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap";

/** Load the Gate Desk typefaces once; silently falls back to system fonts when offline. */
export function loadGateFonts() {
    if (document.getElementById("gd-fonts")) {
        return;
    }
    const link = document.createElement("link");
    link.id = "gd-fonts";
    link.rel = "stylesheet";
    link.href = FONT_URL;
    document.head.appendChild(link);
}

export const HOME_ACTION = "gate_management.action_gate_desk_home";

export function goHome(actionService) {
    return actionService.doAction(HOME_ACTION, { clearBreadcrumbs: true });
}

let toastTimer = null;
/** Small dark toast in the Gate Desk identity (used next to Odoo's notifications for quick confirmations). */
export function gateToast(message) {
    let el = document.getElementById("gd-toast");
    if (!el) {
        el = document.createElement("div");
        el.id = "gd-toast";
        el.className = "gd-toast";
        el.innerHTML = '<i class="fa fa-check"></i><span></span>';
        document.body.appendChild(el);
    }
    el.querySelector("span").textContent = message;
    el.classList.add("gd-show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("gd-show"), 2400);
}

export function nowHM() {
    return new Date().toTimeString().slice(0, 5);
}
