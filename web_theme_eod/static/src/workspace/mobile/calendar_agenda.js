/** @odoo-module **/
// Phone calendar: an agenda — the events of the period shown as a list by day (today marked), which reads far
// better on a narrow screen than a week grid. It is the default on phones, remembered per device; Grid brings
// the usual calendar back. The arrows, Today and the month picker still move through periods, and tapping an
// event opens it the way the calendar does. Desktop is unchanged.
import { patch } from "@web/core/utils/patch";
import { proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { CalendarController } from "@web/views/calendar/calendar_controller";

const KEY = "aic.calendar.agenda";

function readPref() {
    try {
        return browser.localStorage.getItem(KEY) !== "0";
    } catch {
        return true;
    }
}

patch(CalendarController.prototype, {
    setup() {
        super.setup(...arguments);
        this.aicAgenda = proxy({ on: readPref() });
    },
    get aicAgendaOn() {
        return Boolean(this.uiService.isSmall && this.aicAgenda.on && this.model.meta.scale !== "year");
    },
    aicToggleAgenda() {
        this.aicAgenda.on = !this.aicAgenda.on;
        try {
            browser.localStorage.setItem(KEY, this.aicAgenda.on ? "1" : "0");
        } catch {
            // private mode: the choice lasts for this page only
        }
    },
    get aicAgendaDays() {
        const { DateTime } = luxon;
        const today = DateTime.local().toISODate();
        const days = new Map();
        const records = Object.values(this.model.records || {}).sort((a, b) => a.start - b.start);
        for (const rec of records) {
            const key = rec.start.toISODate();
            if (!days.has(key)) {
                days.set(key, {
                    key,
                    label: rec.start.toLocaleString(DateTime.DATE_MED_WITH_WEEKDAY),
                    isToday: key === today,
                    items: [],
                });
            }
            days.get(key).items.push({
                id: rec.id,
                record: rec,
                title: rec.title,
                time: rec.isAllDay || rec.isTimeHidden
                    ? _t("All day")
                    : `${rec.start.toLocaleString(DateTime.TIME_SIMPLE)} – ${rec.end.toLocaleString(DateTime.TIME_SIMPLE)}`,
                color: rec.colorIndex,
            });
        }
        return [...days.values()];
    },
    aicOpenAgendaItem(item) {
        this.editRecord(item.record);
    },
});
