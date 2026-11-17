/** @odoo-module **/
// The top bar (web.NavBar, both editions — Enterprise's navbar extends it):
//   * a ☰ toggle at the very start to show / hide the desktop left pane — the only change to the
//     navbar's markup: nothing is removed or moved, the button simply prepends;
//   * on a phone, the Core tab bar opens Odoo's OWN app drawer through the bus
//     ("AIC:APP-DRAWER", detail "apps" | "menu") — the drawer, its sections and its "All Apps"
//     list (Enterprise: the home menu) are Odoo's, the theme only restyles them.
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { useBus, useService } from "@web/core/utils/hooks";

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.aicPrefs = useService("aic_prefs");
        this.aicUi = useService("ui");
        useBus(this.env.bus, "AIC:APP-DRAWER", ({ detail }) => this.aicOpenDrawer(detail));
    },
    get aicPaneAvailable() {
        // only meaningful on desktop with a pane layout chosen
        return !this.aicUi.isSmall && this.aicPrefs.prefs.nav !== "top";
    },
    toggleAicPane() {
        this.aicPrefs.setLocal({ paneOpen: !this.aicPrefs.state.paneOpen });
    },
    async aicOpenDrawer(what) {
        if (what === "apps") {
            // Community: the drawer's "All Apps" list; Enterprise: its home menu (the app grid)
            this.state.isAllAppsMenuOpened = false;
            this.state.isAppMenuSidebarOpened = true;
            this.onAllAppsBtnClick();
            return;
        }
        // "menu": the current app's sections. Enterprise draws the drawer only inside an app,
        // so leave its home menu first.
        if (this.hm && this.hm.hasHomeMenu) {
            await this.hm.toggle(false);
        }
        this.state.isAllAppsMenuOpened = false;
        this.state.isAppMenuSidebarOpened = true;
    },
});
