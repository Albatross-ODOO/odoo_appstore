/** @odoo-module **/
// Schedule Activity: one-tap due dates under the date field — Today, Tomorrow, Next week (the first day of next
// week in the user's language) and In 2 weeks. The pick matching the current date is highlighted; the date field
// stays for any other day. Placed by views/mail_activity_views.xml in the schedule wizard and the activity form.
import { Component, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const { DateTime } = luxon;

export class AicDatePicks extends Component {
    static template = "aic_workspace.DatePicks";
    props = useProps({ ...standardWidgetProps, fieldName: t.string().optional("date_deadline") });

    get picks() {
        const today = DateTime.local().startOf("day");
        const weekStart = localization.weekStart || 1;   // 1 = Monday … 7 = Sunday, as luxon's weekday
        let nextWeek = today.plus({ days: 1 });
        while (nextWeek.weekday !== weekStart) {
            nextWeek = nextWeek.plus({ days: 1 });
        }
        return [
            { key: "today", label: _t("Today"), date: today },
            { key: "tomorrow", label: _t("Tomorrow"), date: today.plus({ days: 1 }) },
            { key: "next_week", label: _t("Next week"), date: nextWeek },
            { key: "two_weeks", label: _t("In 2 weeks"), date: today.plus({ weeks: 2 }) },
        ];
    }
    isActive(pick) {
        const value = this.props.record.data[this.props.fieldName];
        return Boolean(value && value.hasSame(pick.date, "day"));
    }
    dateLabel(pick) {
        return pick.date.toLocaleString(DateTime.DATE_MED_WITH_WEEKDAY);
    }
    pick(pick) {
        this.props.record.update({ [this.props.fieldName]: pick.date });
    }
}

registry.category("view_widgets").add("aic_date_picks", {
    component: AicDatePicks,
    extractProps: ({ attrs }) => ({ fieldName: attrs.field || "date_deadline" }),
});
