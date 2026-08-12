/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { notificationPermissionService } from "@mail/core/common/notification_permission_service";

import { reactive } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { isAndroidApp, isIosApp } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
const { onWillStart } = owl;

patch(WebClient.prototype, {
    setup() {
      "use strict";
        super.setup();
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.title.setParts({ zopenerp: session.brand_name || "" });
        onWillStart(async () =>{
            const branding_data = await this.orm.call('res.company', 'get_current_company_brand_details', [], { context: session.user_context });
            this.brandName = branding_data && branding_data.brand_name;
            this.CompanyName = branding_data && branding_data.company_name;
            const brand_name = this.brandName || this.CompanyName;
            this.title.setParts({ zopenerp: brand_name }); // zopenerp is easy to grep
        });
    },
});

patch(Dialog.prototype, {
    setup() {
        super.setup();
        this.props.title = this.props && this.props.title.replace(new RegExp("Odoo", "g"), "");
    },
});