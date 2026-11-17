/** @odoo-module **/
// CRM "Mark Lost" dialog in one tap: picking a reason marks the lead lost straight away (through the dialog's own
// Mark as Lost button, so saving, closing and reloading are Odoo's), and a toast offers Undo, which restores the
// lead. The closing note sits above the reasons (lost_one_tap.scss) so it can be written before the tap. Nothing
// here depends on CRM: the patch only wakes up for the crm.lead.lost wizard.
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";

const LOST_MODEL = "crm.lead.lost";
const APPLY = "action_lost_reason_apply";
const REASON_BADGE = "[name=lost_reason_id] .o_selection_badge:not(.o-dropdown-caret)";

function displayName(value) {
    return value ? value.display_name ?? value[1] ?? "" : "";
}

// Undo: leads whose probability followed the stage are restored the Odoo way (recomputed); a probability set by
// hand is written back as it was
async function aicUndoLost(orm, leads) {
    const automated = leads.filter((l) => l.probability === l.automated_probability).map((l) => l.id);
    const manual = leads.filter((l) => l.probability !== l.automated_probability);
    if (automated.length) {
        await orm.call("crm.lead", "action_restore", [automated]);
    }
    if (manual.length) {
        await orm.call("crm.lead", "action_unarchive", [manual.map((l) => l.id)]);
        const byValue = Map.groupBy(manual, (l) => l.probability);
        for (const [probability, group] of byValue) {
            await orm.write("crm.lead", group.map((l) => l.id), { probability });
        }
    }
}

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.props.resModel !== LOST_MODEL) {
            return;
        }
        const onClick = (ev) => {
            if (ev.target.closest(REASON_BADGE)) {
                this.aicApplyLost();
            }
        };
        onMounted(() => this.aicRootEl()?.addEventListener("click", onClick));
        onWillUnmount(() => this.aicRootEl()?.removeEventListener("click", onClick));
    },
    aicRootEl() {
        return this.rootRef.el;
    },
    async aicApplyLost() {
        // the badge updates the record on the same click; give it a moment to land
        for (let i = 0; i < 20 && !this.model.root.data.lost_reason_id; i++) {
            await new Promise((resolve) => setTimeout(resolve, 25));
        }
        if (!this.model.root.data.lost_reason_id) {
            return; // the reason was deselected
        }
        const modal = this.aicRootEl()?.closest(".modal");
        modal?.querySelector(`button[name=${APPLY}]`)?.click();
    },
    async beforeExecuteActionButton(clickParams) {
        if (this.props.resModel === LOST_MODEL && clickParams.name === APPLY) {
            const data = this.model.root.data;
            const ids = [...(data.lead_ids?.currentIds || [])];
            // remember each lead's probability so that Undo puts back exactly what was there
            const leads = ids.length
                ? await this.env.services.orm.read("crm.lead", ids, ["probability", "automated_probability"])
                : [];
            this.aicLost = { ids, leads, reason: displayName(data.lost_reason_id) };
        }
        return super.beforeExecuteActionButton(...arguments);
    },
    async afterExecuteActionButton(clickParams) {
        await super.afterExecuteActionButton(...arguments);
        const lost = this.props.resModel === LOST_MODEL && clickParams.name === APPLY && this.aicLost;
        if (!lost || !lost.ids.length) {
            return;
        }
        this.aicLost = null;
        // the dialog is closed by now: use the services straight from the env
        const { notification, orm, action } = this.env.services;
        const close = notification.add(
            lost.reason ? _t("Marked as lost: %(reason)s", { reason: lost.reason }) : _t("Marked as lost"),
            {
                type: "info",
                buttons: [
                    {
                        name: _t("Undo"),
                        primary: true,
                        onClick: async () => {
                            close();
                            await aicUndoLost(orm, lost.leads);
                            await action.doAction("soft_reload");
                        },
                    },
                ],
            }
        );
    },
});
