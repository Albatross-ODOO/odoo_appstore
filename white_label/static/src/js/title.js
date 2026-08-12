/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { onWillStart } from "@odoo/owl";

patch(WebClient.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        if (session.brand_name) {
            this.title.setParts({ zopenerp: session.brand_name });
        }
        onWillStart(async () => {
            try {
                const branding_data = await this.orm.call('res.company', 'get_current_company_brand_details', [], { context: session.user_context });
                this.brandName = branding_data && branding_data.brand_name;
                this.CompanyName = branding_data && branding_data.company_name;
                const brand_name = this.brandName || this.CompanyName;
                if (brand_name) {
                    this.title.setParts({ zopenerp: brand_name });
                }
            } catch (e) {
                // Ignore if query fails
            }
        });
    },
});

patch(Dialog.prototype, {
    setup() {
        super.setup();
        if (this.props && this.props.title && typeof this.props.title === "string") {
            this.props.title = this.props.title.replace(/Odoo/g, "");
        }
    },
});