/** @odoo-module **/
// Archive, then Undo: after records are archived (a list's or kanban's Actions menu, a kanban card's menu, a form's
// gear menu), a toast says how many and offers Undo, which unarchives exactly those records and reloads the view.
// Odoo's own confirmation before archiving stays; the archive itself is Odoo's.
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { DynamicList } from "@web/model/relational_model/dynamic_list";
import { Record } from "@web/model/relational_model/record";

function offerUndo(model, resModel, resIds, context) {
    if (!resIds.length) {
        return;
    }
    const close = model.notification.add(
        resIds.length === 1 ? _t("Archived.") : _t("%(n)s records archived.", { n: resIds.length }),
        {
            type: "info",
            buttons: [{
                name: _t("Undo"),
                primary: true,
                onClick: async () => {
                    close();
                    await model.orm.call(resModel, "action_unarchive", [resIds], { context });
                    await model.load();
                },
            }],
        }
    );
}

patch(DynamicList.prototype, {
    async archive(isSelected) {
        const resIds = [...(await this.getResIds(isSelected))];
        const result = await super.archive(...arguments);
        offerUndo(this.model, this.resModel, resIds, this.context);
        return result;
    },
});

patch(Record.prototype, {
    async archive() {
        const resIds = this.resId ? [this.resId] : [];
        const result = await super.archive(...arguments);
        offerUndo(this.model, this.resModel, resIds, this.context);
        return result;
    },
});
