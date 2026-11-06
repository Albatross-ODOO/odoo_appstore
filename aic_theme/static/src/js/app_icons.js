/** @odoo-module **/
// Line app icons: a known app's icon becomes one stroke glyph in the action colour on a light tile
// (the Home "Your apps" of the design study), drawn as an SVG and handed out as the menu's own
// webIconData, so every place that shows app icons (Enterprise app grid, top bar, Community drawer,
// command palette, Home, left pane, phone tab bar) shows it without a template change. Apps the set
// does not know, and icons customised in Studio, keep Odoo's icon. Company setting "App icons".
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

// key: the module of the menu's web_icon ("sale_management,static/description/icon.png"),
// or module:file where one module ships several icons. 24 px grid, round caps and joins.
export const AIC_APP_GLYPHS = {
    aic_home: "M3 11l9-7 9 7M5 9.5V20h5v-6h4v6h5V9.5",
    mail: "M4 5h16v11H9l-5 4z",
    project_todo: "M4 4h16v16H4zM8 12l3 3 5-6",
    calendar: "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4",
    appointment: "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4M9 15l2 2 4-4",
    contacts: "M16 19a4 4 0 0 0-8 0M12 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6M4 3h16v18H4z",
    crm: "M12 3a9 9 0 1 0 9 9M12 7a5 5 0 1 0 5 5M12 11a1 1 0 1 0 1 1",
    sale_management: "M4 19V9m6 10V5m6 14v-7m4 7H2",
    sale: "M4 19V9m6 10V5m6 14v-7m4 7H2",
    sale_subscription: "M17 2l3 3-3 3M4 11V9a4 4 0 0 1 4-4h12M7 22l-3-3 3-3M20 13v2a4 4 0 0 1-4 4H4",
    sale_renting: "M7.5 16.5a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9zM12 12h9M18 12v3M21 12v2",
    spreadsheet_dashboard: "M4 4h7v9H4zM13 4h7v5h-7zM13 11h7v9h-7zM4 15h7v5H4z",
    point_of_sale: "M4 9h16l-1.5-5h-13zM5 9v11h14V9M10 20v-5h4v5",
    pos_enterprise: "M7 21h10M7 21v-6M17 21v-6M6 15a4 4 0 0 1-.6-8A5 5 0 0 1 12 3a5 5 0 0 1 6.6 4A4 4 0 0 1 18 15z",
    account: "M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6",
    accountant: "M6 3h12v18H6zM9 7h6M9 12h.01M12 12h.01M15 12h.01M9 16h.01M12 16h.01M15 16h.01",
    account_consolidation: "M4 4h6v6H4zM14 14h6v6h-6zM7 10v4h7",
    equity: "M12 3v9h9M21 12a9 9 0 1 1-9-9",
    project: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
    planning: "M4 4v16h16M8 8h6M10 12h8M7 16h5",
    hr_timesheet: "M12 21a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM12 9v4l2 2M10 2h4M12 2v3",
    helpdesk: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM5.6 5.6l3.6 3.6M14.8 14.8l3.6 3.6M18.4 5.6l-3.6 3.6M9.2 14.8l-3.6 3.6",
    industry_fsm: "M12 21s7-6 7-12a7 7 0 0 0-14 0c0 6 7 12 7 12zM12 11a2 2 0 1 0 0-4 2 2 0 0 0 0 4z",
    purchase: "M3 4h2l2.4 11h10.2L20 8H6.3M9 20h.01M17 20h.01",
    stock: "M3 8l9-5 9 5v8l-9 5-9-5zM3 8l9 5 9-5M12 13v8",
    stock_barcode: "M4 6v12M7 6v12M11 6v12M13 6v12M17 6v12M20 6v12",
    mrp: "M3 20V10l5 3v-3l5 3V6h4l1 14zM3 20h18",
    mrp_workorder: "M4 4h16v12H4zM9 20h6M12 16v4M8 12l3-3 2 2 3-3",
    mrp_plm: "M12 3l9 5-9 5-9-5zM3 12l9 5 9-5M3 16l9 5 9-5",
    quality_control: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4",
    maintenance: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM12 2v3M12 19v3M4.9 4.9L7 7M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1L7 17M17 7l2.1-2.1",
    repair: "M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z",
    hr: "M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM3 20a6 6 0 0 1 12 0M16 5.5a3 3 0 0 1 0 5.5M18 20a6 6 0 0 0-3-5.2",
    hr_recruitment: "M10 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM3 21a7 7 0 0 1 14 0M19 8v6M16 11h6",
    hr_referral: "M4 10h16v4H4zM6 14v7h12v-7M12 10v11M12 10c-2 0-5-1-4.5-3.5S12 7 12 10zM12 10c2 0 5-1 4.5-3.5S12 7 12 10z",
    hr_appraisal: "M12 3l2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3l-5.5 2.9 1-6.2L3 9.6l6.2-.9z",
    hr_attendance: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2",
    hr_holidays: "M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
    hr_expense: "M3 7h18v12H3zM3 7l13-3v3M16 13h2",
    hr_payroll: "M3 6h18v12H3zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 9v.01M18 15v.01",
    fleet: "M5 17h14M5 17v-5l2-5h10l2 5v5M5 12h14M7 17v2M17 17v2M8 14.5h.01M16 14.5h.01",
    lunch: "M7 3v8M5 3v4a2 2 0 0 0 4 0V3M7 11v10M17 3c-2 0-3 3-3 7h3v11",
    membership: "M3 5h18v14H3zM9 11a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM5.5 16a3.5 3.5 0 0 1 7 0M14 9h4M14 13h4",
    approvals: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM8 12l3 3 5-6",
    documents: "M3 6h6l2 2h10v11H3z",
    sign: "M16 3l5 5L9 20H4v-5zM13 6l5 5M3 22h18",
    knowledge: "M4 5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2zM4 5v16M8 7h8",
    website: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18",
    website_slides: "M2 9l10-5 10 5-10 5zM6 11v5c3 2 9 2 12 0v-5M22 9v6",
    event: "M4 6h16v4a2 2 0 0 0 0 4v4H4v-4a2 2 0 0 0 0-4zM14 6v12",
    survey: "M8 3h8v3H8zM6 4.5H5V21h14V4.5h-1M9 11h6M9 15h4",
    mass_mailing: "M3 5h18v14H3zM3 6l9 7 9-7",
    mass_mailing_sms: "M7 3h10v18H7zM11 18h2",
    marketing_automation: "M5 4h6v5H5zM13 15h6v5h-6zM8 9v3h8v3",
    marketing_card: "M3 5h18v14H3zM3 15l5-4 4 3 3-2 6 4",
    social: "M18 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM18 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8.6 13.5l6.8 4M15.4 6.5l-6.8 4",
    utm: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
    im_livechat: "M4 4h12v9H8l-4 3zM20 9v10l-3-2h-7",
    whatsapp: "M21 12a9 9 0 0 1-13.5 7.8L3 21l1.2-4.5A9 9 0 1 1 21 12z",
    voip: "M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2",
    room: "M6 21V3h12v18M3 21h18M14 12h.01",
    frontdesk: "M4 17h16M6 17a6 6 0 0 1 12 0M12 8V6M10 6h4M3 20h18",
    esg: "M5 19c0-8 5-14 15-14 0 10-6 15-14 15M5 19l7-7",
    iot: "M7 7h10v10H7zM10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4",
    ai_agentic: "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z",
    data_recycle: "M4 20h7M14 4l6 6-9 9-6-6zM9 9l6 6",
    databases: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
    "base:modules.png": "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM17 14v6M14 17h6",
    "base:settings.png": "M4 7h10M18 7h2M4 17h4M12 17h8M16 5v4M10 15v4",
    "base:exception.png": "M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3M7 15h10",
};

export function aicGlyphKey(webIcon) {
    if (!webIcon || typeof webIcon !== "string" || !webIcon.includes(",")) {
        return null;
    }
    const [module, path] = webIcon.split(",");
    if (!path || !/(^|\/)static\//.test(path.trim())) {
        return null; // "fa-x,#color,#bg": an icon picked in Studio stays as chosen
    }
    const file = path.split("/").pop();
    const key = `${module.trim()}:${file}`;
    return key in AIC_APP_GLYPHS ? key : module.trim() in AIC_APP_GLYPHS ? module.trim() : null;
}

function readColours() {
    const css = getComputedStyle(document.body);
    const get = (name, fallback) => css.getPropertyValue(name).trim() || fallback;
    return {
        ink: get("--nm-action", "#0060D6"),
        fill: get("--gl-pane-hi", get("--nm-surface-high", "#FFFFFF")),
        edge: get("--nm-hairline", "rgba(17,19,24,.10)"),
    };
}

export function aicLineIconUri(d, colours) {
    const svg =
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 56 56">` +
        // drawn small (top bar, command palette, drawer rows) the tile would crowd the glyph:
        // below 36 px the image is the bare glyph, filling the box
        `<style>@media (max-width: 36px) { rect { display: none } g { transform: translate(2px, 2px) scale(2.17) } }</style>` +
        `<rect x=".5" y=".5" width="55" height="55" rx="16" fill="${colours.fill}" stroke="${colours.edge}"/>` +
        `<g transform="translate(16 16)" fill="none" stroke="${colours.ink}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">` +
        `<path d="${d}"/></g></svg>`;
    // the "aic=line" parameter marks the image for the stylesheet (shadow, corner radius)
    return "data:image/svg+xml;aic=line;charset=utf-8," + encodeURIComponent(svg);
}

export function aicLineIconsOn() {
    return session.aic_app_icons === "line" && document.body.classList.contains("o_aic_theme");
}

const menuService = registry.category("services").get("menu");
patch(menuService, {
    async start() {
        const service = await super.start(...arguments);
        if (!aicLineIconsOn()) {
            return service;
        }
        let colours = null;
        const uris = {};
        const dress = (menu) => {
            if (!menu || menu.aicLine !== undefined || menu.id !== menu.appID) {
                return menu;
            }
            const key = aicGlyphKey(menu.webIcon);
            menu.aicLine = Boolean(key);
            if (key) {
                colours = colours || readColours();
                uris[key] = uris[key] || aicLineIconUri(AIC_APP_GLYPHS[key], colours);
                menu.webIconData = uris[key];
                menu.webIconDataMimetype = "image/svg+xml";
            }
            return menu;
        };
        // getApps / getCurrentApp / getMenuAsTree all read through getMenu
        const { getAll, getMenu } = service;
        service.getMenu = (menuId) => dress(getMenu(menuId));
        service.getAll = () => getAll.call(service).map(dress);
        return service;
    },
});
