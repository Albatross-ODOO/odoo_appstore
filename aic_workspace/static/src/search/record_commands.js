/** @odoo-module **/
// Records in the command palette (Ctrl+K): type at least two letters and the matching contacts, opportunities,
// quotations, invoices, purchase orders, transfers, tasks, tickets and products appear in their own group, each
// with its kind and a hint (the customer, the amount). Enter opens the record, Ctrl+Enter in a new tab.
// The server side is aic.search.search_records (one call, Odoo's name_search, the user's access rules).
import { Component, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AicRecordCommand extends Component {
    static template = "aic_workspace.RecordCommand";
    props = useProps({
        kind: t.string().optional(),
        hint: t.string().optional(),
        title: t.string().optional(),
        name: t.any().optional(),
        searchValue: t.any().optional(),
        executeCommand: t.any().optional(),
        slots: t.any().optional(),
    });
}

registry.category("command_categories").add("aic_records", { name: _t("Records") }, { sequence: 40 });

registry.category("command_provider").add("aic_records", {
    provide(options) {
        const orm = useService("orm");
        const action = useService("action");
        const term = (options.searchValue || "").trim();
        if (term.length < 2) {
            return [];
        }
        return orm.silent.call("aic.search", "search_records", [term]).then((records) =>
            records.map((rec) => ({
                Component: AicRecordCommand,
                category: "aic_records",
                // the palette filters its list by fuzzy-matching the command name: the hint and the kind are part
                // of it, so a credit note found by its customer's name stays; the row shows the record's own name
                name: [rec.name, rec.hint, rec.kind].filter(Boolean).join(" "),
                href: `/odoo/${rec.model}/${rec.id}`,
                props: { kind: rec.kind, hint: rec.hint, title: rec.name },
                action() {
                    // nothing returned: the palette closes (a returned object would be read as a new palette)
                    action.doAction({
                        type: "ir.actions.act_window",
                        res_model: rec.model,
                        res_id: rec.id,
                        views: [[false, "form"]],
                        target: "current",
                    });
                },
            }))
        );
    },
});
