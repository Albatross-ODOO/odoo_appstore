/** @odoo-module **/

import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { routeToUrl } from "@web/core/browser/router_service";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
const userMenuRegistry = registry.category("user_menuitems");

import { reactive } from "@odoo/owl";
import { isAndroidApp, isIosApp } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";

patch(UserMenu.prototype, {
    setup() {
        "use strict";
        super.setup();
        userMenuRegistry.remove("documentation");
        userMenuRegistry.remove("support");
        userMenuRegistry.remove("odoo_account");
    },
});

// Herer we remove odoo from push notification to enable browser / device requests
export const notificationPermissionService = {
    dependencies: ["notification"],

    _normalizePermission(permission) {
        switch (permission) {
            case "default":
                return "prompt";
            case undefined:
                return "denied";
            default:
                return permission;
        }
    },

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    async start(env, services) {
        const notification = services.notification;
        let permission;
        try {
            permission = await browser.navigator?.permissions?.query({
                name: "notifications",
            });
        } catch {
            // noop
        }
        const state = reactive({
            /** @type {"prompt" | "granted" | "denied"} */
            permission:
                isIosApp() || isAndroidApp()
                    ? "denied"
                    : this._normalizePermission(
                          permission?.state ?? browser.Notification?.permission
                      ),
            requestPermission: async () => {
                if (browser.Notification && state.permission === "prompt") {
                    state.permission = this._normalizePermission(
                        await browser.Notification.requestPermission()
                    );
                    if (state.permission === "denied") {
                        notification.add(_t("Notifications will not be sent on this device."), {
                            type: "warning",
                            title: _t("Notifications blocked"),
                        });
                    } else if (state.permission === "granted") {
                        notification.add(_t("Notifications will be sent on this device!"), {
                            type: "success",
                            title: _t("Notifications allowed"),
                        });
                    }
                }
            },
        });
        if (permission) {
            permission.addEventListener("change", () => (state.permission = permission.state));
        }
        return state;
    },
};
registry.category("services").remove("mail.notification.permission");
registry.category("services").add("mail.notification.permission", notificationPermissionService);

