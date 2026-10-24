/** @odoo-module **/
// A permanent Home key at the start of the top bar (desktop, both editions): one click back to
// Home from anywhere, without opening the app grid first. Odoo's apps control moves one key right.
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { useService } from "@web/core/utils/hooks";

const HOME_APP = "aic_home.menu_aic_home_root";

patch(NavBar.prototype, {
    setup() {
        super.setup(...arguments);
        this.aicHomeUi = useService("ui");
        this.aicHomeAction = useService("action");
    },
    get aicHomeKeyVisible() {
        // phones reach Home from the tab bar
        return !this.aicHomeUi.isSmall && !this.isScopedApp;
    },
    get aicHomeApp() {
        return this.menuService.getApps().find((app) => app.xmlid === HOME_APP);
    },
    get aicHomeActive() {
        return this.currentApp?.xmlid === HOME_APP && !(this.hm && this.hm.hasHomeMenu);
    },
    async aicGoHome() {
        if (this.hm && this.hm.hasHomeMenu) {
            await this.hm.toggle(false);
        }
        const app = this.aicHomeApp;
        if (app) {
            // through the menu, so the top bar shows Home as the current app
            await this.menuService.selectMenu(app);
        } else {
            await this.aicHomeAction.doAction("aic_home.action_aic_home", { clearBreadcrumbs: true });
        }
    },
});
