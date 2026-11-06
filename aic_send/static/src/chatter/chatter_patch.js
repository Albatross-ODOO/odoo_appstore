/** @odoo-module **/
// Core: a "WhatsApp" button in the chatter top bar of every record (setting: aic_whatsapp_share).
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.aicAction = useService("action");
    },
    get aicWhatsappShare() {
        const thread = this.state.thread;
        return Boolean(session.aic_whatsapp_share && thread && thread.id && thread.model);
    },
    openAicWhatsapp() {
        const thread = this.state.thread;
        return this.aicAction.doAction("aic_send.action_whatsapp_share", {
            additionalContext: { default_res_model: thread.model, default_res_id: thread.id },
            onClose: () => (this.reloadParentView ? this.reloadParentView() : undefined),
        });
    },
});
