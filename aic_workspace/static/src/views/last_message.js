/** @odoo-module **/
// Ticket form: the customer's last message first. A card under the smart buttons quotes what the customer last
// wrote (by e-mail or from the portal), who and when, says whether the team has answered since, and has a Reply
// key that opens the chatter's Send message composer. The card is put into the ticket's form by the web client
// (no dependency on Helpdesk): FormArchParser adds the widget for the models listed below.
import { Component, onWillStart, onWillUpdateProps, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const MODELS = ["helpdesk.ticket"];
const WIDGET = "aic_last_message";

export class AicLastMessage extends Component {
    static template = "aic_workspace.LastMessage";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.root = useRef("root");
        this.state = useState({ msg: false });
        onWillStart(() => this.load(this.props.record));
        onWillUpdateProps((next) => {
            if (next.record.resId !== this.props.record.resId) {
                return this.load(next.record);
            }
        });
    }
    async load(record) {
        // a help, never a blocker: if it cannot be read, the form opens as usual
        try {
            this.state.msg = record.resId
                ? await this.orm.silent.call("mail.message", "aic_last_customer_message", [record.resModel, record.resId])
                : false;
        } catch {
            this.state.msg = false;
        }
    }
    get when() {
        const date = this.state.msg && luxon.DateTime.fromSQL(this.state.msg.date, { zone: "utc" });
        return date && date.isValid ? date.toLocal().toRelative() : "";
    }
    reply() {
        const form = this.root.el?.closest(".o_form_view") || document;
        const send = form.querySelector(".o-mail-Chatter-sendMessage") || document.querySelector(".o-mail-Chatter-sendMessage");
        send?.click();
        send?.closest(".o-mail-Chatter")?.scrollIntoView({ block: "start", behavior: "smooth" });
    }
}
registry.category("view_widgets").add(WIDGET, { component: AicLastMessage });

patch(FormArchParser.prototype, {
    parse(xmlDoc, models, modelName) {
        if (MODELS.includes(modelName) && !xmlDoc.querySelector(`widget[name=${WIDGET}]`)) {
            const sheet = xmlDoc.querySelector("sheet");
            if (sheet) {
                const widget = xmlDoc.ownerDocument.createElement("widget");
                widget.setAttribute("name", WIDGET);
                const box = sheet.querySelector(":scope > div[name=button_box]");
                sheet.insertBefore(widget, box ? box.nextSibling : sheet.firstChild);
            }
        }
        return super.parse(...arguments);
    },
});
