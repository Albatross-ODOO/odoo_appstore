/** @odoo-module **/
// User menu (avatar, top-right; the burger menu on a phone): "Theme preferences" opens the Core
// panel; Community gets a "Dark mode" switch; phones and installed apps a "Developer mode" switch.
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import { router } from "@web/core/browser/router";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";
import { aicPanelState } from "./prefs_panel";

function themePreferencesItem() {
    return {
        type: "item",
        id: "aic_theme_prefs",
        description: _t("Theme preferences"),
        callback: () => {
            aicPanelState.open = true;
        },
        sequence: 45,
    };
}

registry.category("user_menuitems").add("aic_theme_prefs", themePreferencesItem, { sequence: 45 });

// "My profile": the user's own employee record (org chart, resume, time off when those apps are
// installed). Only for a user linked to an employee; Odoo's "My Preferences" stays as it is.
function myProfileItem(env) {
    return {
        type: "item",
        id: "aic_my_profile",
        description: _t("My profile"),
        hide: !session.aic_has_employee,
        callback: async () => {
            const action = await env.services.orm.call("res.users", "aic_my_profile_action", []);
            env.services.action.doAction(action);
        },
        sequence: 49,
    };
}
registry.category("user_menuitems").add("aic_my_profile", myProfileItem, { sequence: 49 });

// Community has no "Dark Mode" entry (web_enterprise adds one): the same switch, driven by the
// theme's own dark scheme (aic_prefs.setMode). Not registered when Enterprise's color_scheme
// service exists, so the Enterprise menu is untouched.
function darkModeItem(env) {
    const prefs = env.services.aic_prefs;
    const dark = prefs.effectiveScheme(prefs.mode) === "dark";
    return {
        type: "switch",
        id: "aic_dark_mode",
        description: _t("Dark mode"),
        isChecked: dark,
        callback: () => prefs.setMode(dark ? "light" : "dark"),
        sequence: 44,
    };
}
if (!registry.category("services").contains("color_scheme")) {
    registry.category("user_menuitems").add("aic_dark_mode", darkModeItem, { sequence: 44 });
}

// Developer mode where there is no address bar to type `?debug=1` in — a phone, or Odoo installed
// as an app (PWA) on a tablet or a desktop: Odoo hides its technical menus (Settings › Groups /
// Technical, ~200 Configuration items) unless the SESSION is in developer mode. The state is the
// server session's (session_info.bundle_params.debug: `odoo.debug` is blanked whenever the URL has
// no `?debug=`); the switch does what Odoo's own "Activate the developer mode" link does.
function developerModeItem(env) {
    const on = !!(session.bundle_params && session.bundle_params.debug);
    return {
        type: "switch",
        id: "aic_dev_mode",
        description: _t("Developer mode"),
        isChecked: on,
        hide: !(env.services.ui.isSmall || isDisplayStandalone()),
        callback: () => router.pushState({ debug: on ? 0 : 1 }, { reload: true }),
        sequence: 46,
    };
}
registry.category("user_menuitems").add("aic_dev_mode", developerModeItem, { sequence: 46 });
