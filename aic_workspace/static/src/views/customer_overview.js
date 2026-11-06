/** @odoo-module **/
// Contact form: the company at a glance under the smart buttons — open quotations, unpaid invoices (overdue
// ones in red), open tickets, the last delivery and the next activity, from the apps that are installed. Each
// chip opens the matching records. Nothing is shown for a new contact or when there is nothing to tell.
import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class AicCustomerOverview extends Component {
    static template = "aic_workspace.CustomerOverview";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ chips: [] });
        onWillStart(() => this.load(this.props.record.resId));
        onWillUpdateProps((next) => {
            if (next.record.resId !== this.props.record.resId) {
                return this.load(next.record.resId);
            }
        });
    }
    async load(resId) {
        // a help, never a blocker: if it cannot be read, the contact opens as usual
        try {
            this.state.chips = resId ? await this.orm.silent.call("res.partner", "aic_customer_overview", [[resId]]) : [];
        } catch {
            this.state.chips = [];
        }
    }
    open(chip) {
        if (!chip.action) {
            return;
        }
        const a = chip.action;
        this.action.doAction({
            type: "ir.actions.act_window", name: a.name, res_model: a.res_model,
            ...(a.res_id ? { res_id: a.res_id, views: [[false, "form"]] } : { domain: a.domain, views: [[false, "list"], [false, "form"]] }),
        });
    }
}
registry.category("view_widgets").add("aic_customer_overview", { component: AicCustomerOverview });
