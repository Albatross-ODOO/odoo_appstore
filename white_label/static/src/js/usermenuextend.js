/** @odoo-module **/

import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

const userMenuRegistry = registry.category("user_menuitems");

patch(UserMenu.prototype, {
    setup() {
        super.setup();
        ["documentation", "support", "account", "odoo_account"].forEach((key) => {
            if (userMenuRegistry.contains(key)) {
                userMenuRegistry.remove(key);
            }
        });
    },
});
