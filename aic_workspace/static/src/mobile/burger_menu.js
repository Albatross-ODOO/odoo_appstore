/** @odoo-module **/
// Phones: the Account tab of the Core tab bar opens Odoo's OWN burger menu (the user, the
// companies, the user-menu entries — Preferences, Install, Log out, and the theme's own), through the
// bus: the burger's toggle lives in the top bar and may be off screen. Enterprise's burger
// extends this one, so both editions answer.
import { patch } from "@web/core/utils/patch";
import { useBus } from "@web/core/utils/hooks";
import { BurgerMenu } from "@web/webclient/burger_menu/burger_menu";

patch(BurgerMenu.prototype, {
    setup() {
        super.setup(...arguments);
        useBus(this.env.bus, "AIC:BURGER", () => this._openBurger());
    },
});
