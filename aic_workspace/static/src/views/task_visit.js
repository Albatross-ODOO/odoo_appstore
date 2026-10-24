/** @odoo-module **/
// A task as a visit (no dependency on Project: the card is put into the task form by the web client): for an open
// task with a customer, the technician sees who, where (with a map link), a call key, the deadline and how far the
// sub-tasks are — before scrolling. Parts and the customer's sign-off are Field Service's own (Enterprise) when
// it is installed.
import { Component, onWillStart, onWillUpdateProps, proxy, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const { DateTime } = luxon;

export class AicTaskVisit extends Component {
    static template = "aic_workspace.TaskVisit";
    props = useProps({ ...standardWidgetProps });

    setup() {
        this.orm = useService("orm");
        this.state = proxy({ visit: false });
        onWillStart(() => this.load(this.props.record));
        onWillUpdateProps((next) => {
            const d = next.record.data, p = this.props.record.data;
            if (next.record.resId !== this.props.record.resId || d.partner_id?.id !== p.partner_id?.id || d.state !== p.state) {
                return this.load(next.record);
            }
        });
    }
    async load(record) {
        try {
            this.state.visit = record.resId ? await this.orm.silent.call("aic.project.summary", "task_visit", [record.resId]) : false;
        } catch {
            this.state.visit = false;
        }
    }
    get deadline() {
        const v = this.state.visit;
        if (!v.deadline) {
            return "";
        }
        const date = DateTime.fromSQL(v.deadline, { zone: "utc" }).toLocal();
        const label = date.toLocaleString({ weekday: "short", day: "numeric", month: "short" });
        return this.late ? _t("Overdue since %(date)s", { date: label }) : _t("Due %(date)s", { date: label });
    }
    get late() {
        const v = this.state.visit;
        return Boolean(v.deadline) && DateTime.fromSQL(v.deadline, { zone: "utc" }) < DateTime.utc();
    }
    get subtasks() {
        const v = this.state.visit;
        return v.subtasks ? _t("%(done)s of %(total)s sub-tasks done", { done: v.subtasks_done, total: v.subtasks }) : "";
    }
}
registry.category("view_widgets").add("aic_task_visit", { component: AicTaskVisit });

patch(FormArchParser.prototype, {
    parse(xmlDoc, models, modelName) {
        if (modelName === "project.task" && !xmlDoc.querySelector("widget[name=aic_task_visit]")) {
            const sheet = xmlDoc.querySelector("sheet");
            if (sheet) {
                const widget = xmlDoc.ownerDocument.createElement("widget");
                widget.setAttribute("name", "aic_task_visit");
                const box = sheet.querySelector(":scope > div[name=button_box]");
                sheet.insertBefore(widget, box ? box.nextSibling : sheet.firstChild);
            }
        }
        return super.parse(...arguments);
    },
});
