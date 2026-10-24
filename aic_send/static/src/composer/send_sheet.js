/** @odoo-module **/
// One send sheet: Odoo's "Send by email" dialog (the mail composer, for one record) gets a channel switch at the
// top — Email or WhatsApp. WhatsApp hands over to the Share on WhatsApp sheet for the same record (its message
// carries the document's secure link, where the customer reads the PDF); Email stays the composer. In the composer,
// a PDF attachment (the quotation, the invoice…) has a Preview key that opens it in Odoo's viewer instead of
// downloading it. The switch is put into the composer's form by the web client, only while the setting is on.
import { Component } from "@odoo/owl";
import { session } from "@web/session";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { FileModel } from "@web/core/file_viewer/file_model";
import { useFileViewer } from "@web/core/file_viewer/file_viewer_hook";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { MailComposerAttachmentList } from "@mail/core/web/mail_composer_attachment_list";

const WIDGET = "aic_send_channel";

function singleResId(record) {
    const raw = record.data.res_ids;
    let ids = [];
    try {
        ids = Array.isArray(raw) ? raw : JSON.parse(raw || "[]");
    } catch {
        ids = [];
    }
    return ids.length === 1 ? ids[0] : false;
}

export class AicSendChannel extends Component {
    static template = "aic_send.SendChannel";
    static props = { ...standardWidgetProps };

    setup() {
        this.action = useService("action");
    }
    get target() {
        const data = this.props.record.data;
        if (!session.aic_whatsapp_share || data.composition_mode !== "comment" || data.subtype_is_log || !data.model) {
            return false;
        }
        const resId = singleResId(this.props.record);
        return resId ? { model: data.model, resId } : false;
    }
    async toWhatsapp() {
        const { model, resId } = this.target;
        this.env.dialogData?.close?.();
        await this.action.doAction("aic_send.action_whatsapp_share", {
            additionalContext: { default_res_model: model, default_res_id: resId },
        });
    }
}
registry.category("view_widgets").add(WIDGET, { component: AicSendChannel });

patch(FormArchParser.prototype, {
    parse(xmlDoc, models, modelName) {
        if (modelName === "mail.compose.message" && session.aic_whatsapp_share && !xmlDoc.querySelector(`widget[name=${WIDGET}]`)) {
            const widget = xmlDoc.ownerDocument.createElement("widget");
            widget.setAttribute("name", WIDGET);
            xmlDoc.insertBefore(widget, xmlDoc.firstChild);
        }
        return super.parse(...arguments);
    },
});

patch(MailComposerAttachmentList.prototype, {
    setup() {
        super.setup(...arguments);
        this.aicFileViewer = useFileViewer();
    },
    aicIsPdf(file) {
        return file.mimetype === "application/pdf" || /\.pdf$/i.test(file.name || "");
    },
    aicPreview(file) {
        const model = Object.assign(new FileModel(), { id: file.id, name: file.name, mimetype: "application/pdf" });
        this.aicFileViewer.open(model);
    },
});
