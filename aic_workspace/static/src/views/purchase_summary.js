/** @odoo-module **/
// Purchase order in plain words (no dependency on Purchase: the card is put into the form by the web client): a
// confirmed order with lines past their expected date starts with "Late from the vendor" — each line, what is still
// to receive and how late — the sales orders it holds up (open in one tap), and Chase vendor, Odoo's own reminder
// e-mail in its composer.
import { Component, onWillStart, onWillUpdateProps, proxy, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class AicPurchaseLate extends Component {
    static template = "aic_workspace.PurchaseLate";
    props = useProps({ ...standardWidgetProps });

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = proxy({ data: false });
        onWillStart(() => this.load(this.props.record));
        onWillUpdateProps((next) => {
            if (next.record.resId !== this.props.record.resId || next.record.data.state !== this.props.record.data.state) {
                return this.load(next.record);
            }
        });
    }
    async load(record) {
        try {
            this.state.data = record.resId ? await this.orm.silent.call("aic.purchase.summary", "purchase_late", [record.resId]) : false;
        } catch {
            this.state.data = false;
        }
    }
    line(l) {
        return _t("%(left)s of %(ordered)s %(uom)s still to receive", l);
    }
    late(l) {
        if (l.days <= 0) {
            return _t("due today");
        }
        return l.days === 1 ? _t("1 day late") : _t("%(n)s days late", { n: l.days });
    }
    openSale(s) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "sale.order", res_id: s.id, views: [[false, "form"]] });
    }
    async chase() {
        const action = await this.orm.call("aic.purchase.summary", "chase_vendor_action", [this.props.record.resId]);
        if (action) {
            this.action.doAction(action, { onClose: () => this.props.record.load() });
        }
    }
}
registry.category("view_widgets").add("aic_purchase_late", { component: AicPurchaseLate });

patch(FormArchParser.prototype, {
    parse(xmlDoc, models, modelName) {
        if (modelName === "purchase.order" && !xmlDoc.querySelector("widget[name=aic_purchase_late]")) {
            const sheet = xmlDoc.querySelector("sheet");
            if (sheet) {
                const widget = xmlDoc.ownerDocument.createElement("widget");
                widget.setAttribute("name", "aic_purchase_late");
                const box = sheet.querySelector(":scope > div[name=button_box]");
                sheet.insertBefore(widget, box ? box.nextSibling : sheet.firstChild);
            }
        }
        return super.parse(...arguments);
    },
});
