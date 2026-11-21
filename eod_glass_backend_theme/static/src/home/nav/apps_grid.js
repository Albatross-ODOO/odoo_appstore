/** @odoo-module **/
// Community, desktop: the top bar the way the demo (Enterprise) shows it. Odoo Community has no full-screen
// app menu, only a 9-dot button that opens a text list next to a separate app-name pill. While the look is on,
// that button becomes one key with the current app's icon and name, and its menu a full-screen grid of app
// keys (apps_grid.xml / apps_grid.scss). Enterprise never renders web.NavBar.AppsMenu on a desktop (it
// replaces that t-call with its home-menu toggle), so it is untouched; with the look off Community stays stock.
import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { session } from "@web/session";

patch(NavBar.prototype, {
    get aicAppGrid() {
        return Boolean(session.aic_skin);
    },
    get aicGridApp() {
        return this.menuService.getCurrentApp() || null;
    },
});
