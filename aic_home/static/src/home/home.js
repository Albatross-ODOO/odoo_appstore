/** @odoo-module **/
// Home: the role-aware start screen. One server call (aic.home.get_home_data) fills it;
// everything else is navigation through the action and menu services.
import { Component, onWillStart, proxy, signal, useProps } from "@odoo/owl";
import { ActivityMarkAsDone } from "@mail/core/web/activity_markasdone_popover";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const OWN_APP = "aic_home.menu_aic_home_root";

export class AicHome extends Component {
    static template = "aic_home.Home";
    props = useProps({ ...standardActionServiceProps });

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.menu = useService("menu");
        this.notification = useService("notification");
        this.store = useService("mail.store");
        // the same Mark Done popover as the chatter: feedback note, Done, Done & Schedule Next, Discard
        this.markDonePopover = usePopover(ActivityMarkAsDone, { position: "left" });
        this.state = proxy({ loading: true, data: null, busy: false, customise: null, moreApps: false, view: "today", week: null, refusing: false, refuseReason: "" });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.data = await this.orm.call("aic.home", "get_home_data", []);
        this.state.loading = false;
    }

    // ------------------------------------------------------------------ derived
    get data() {
        return this.state.data;
    }
    get apps() {
        // the person's own order first (Customise home), then the role's, then the menu's
        const own = this.data?.layout?.app_order || [];
        const hidden = new Set(this.data?.layout?.app_hidden || []);
        const order = this.data?.app_order || [];
        const badges = this.data?.app_badges || {};
        const rank = (list, app) => {
            const i = list.indexOf(this.appKey(app));
            return i === -1 ? list.length : i;
        };
        return this.menu
            .getApps()
            .filter((app) => app.xmlid !== OWN_APP)
            .map((app, index) => ({ app, index, badge: badges[app.xmlid] || 0 }))
            .sort((a, b) => rank(own, a.app) - rank(own, b.app) || rank(order, a.app) - rank(order, b.app) || a.index - b.index)
            .map(({ app, badge }) => ({
                id: app.id,
                key: this.appKey(app),
                name: app.name,
                xmlid: app.xmlid,
                icon: app.webIconData,
                faIcon: app.webIcon,
                badge,
                menu: app,
                hidden: hidden.has(this.appKey(app)),
            }));
    }
    appKey(app) {
        return app.xmlid || String(app.id);
    }
    get shownApps() {
        return this.apps.filter((app) => !app.hidden);
    }
    get hiddenApps() {
        return this.apps.filter((app) => app.hidden);
    }
    get moreAppsLabel() {
        return _t("More apps (%s)", this.hiddenApps.length);
    }
    // whole sentences with placeholders, so translators can order the words for their language
    get greetingLine() {
        return _t("%(greeting)s, %(name)s", { greeting: this.data.greeting, name: this.data.user.first });
    }
    get queueLabel() {
        return _t("Start my queue · %s", this.data.queue.due);
    }
    get customiseFor() {
        return _t("For your %s home. Only you see this.", this.data.role_label);
    }
    toneClass(tone) {
        return `o_aic_tone_${tone || "plain"}`;
    }

    // ------------------------------------------------------------------ navigation
    openRecord(item) {
        if (!item.model || !item.res_id) {
            return;
        }
        if (item.model === "discuss.channel") {
            // a conversation opens in Discuss, not as a record
            return this.action.doAction("mail.action_discuss", { additionalContext: { active_id: `discuss.channel_${item.res_id}` } });
        }
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: item.model,
            res_id: item.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
    openAction(spec) {
        if (!spec) {
            return;
        }
        if (spec.xmlid) {
            return this.action.doAction(spec.xmlid);
        }
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: spec.name,
            res_model: spec.res_model,
            domain: spec.domain,
            context: spec.context || {},
            views: spec.views || [[false, "list"], [false, "kanban"], [false, "form"]],
            target: "current",
        });
    }
    get seeAllMissedLabel() {
        return _t("See all %(count)s", { count: this.data.missed_count });
    }
    get teamOverdueLabel() {
        return _t("Team: %(count)s overdue", { count: this.data.team_overdue_count });
    }
    async openOverdue(scope) {
        const action = await this.orm.call("aic.home", "action_overdue", [scope]);
        return this.action.doAction(action);
    }
    openApp(app) {
        return this.menu.selectMenu(app.menu);
    }
    openQueue() {
        return this.action.doAction("aic_home.action_aic_focus");
    }
    openCleanup(cleanup) {
        return this.action.doAction("aic_home.action_aic_backlog_cleanup", {
            additionalContext: { default_kind: cleanup.kind },
            onClose: () => this.load(),
        });
    }

    // ------------------------------------------------------------------ actions on activities
    async markDone(ev, activityId) {
        if (this.markDonePopover.isOpen) {
            this.markDonePopover.close();
            return;
        }
        const target = ev.currentTarget;
        await this.store.fetchStoreData("mail.activity", { ids: [activityId] });
        const activity = this.store["mail.activity"].get(activityId);
        if (!activity) {
            // gone meanwhile (done elsewhere): just refresh
            return this.load();
        }
        this.markDonePopover.open(target, {
            activity: signal(activity),
            hasHeader: true,
            onActivityChanged: () => {
                this.markDonePopover.close();
                this.notification.add(_t("Marked as done"), { type: "success" });
                this.load();
            },
        });
    }
    async rescheduleMissed() {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const moved = await this.orm.call("aic.home", "reschedule_missed_to_today", []);
            this.notification.add(_t("%s activities moved to today", moved), { type: "success" });
            await this.load();
        } finally {
            this.state.busy = false;
        }
    }
    // a panel key that runs a aic.home method on the server (Failed to send: Retry, Dismiss)
    async runPanelAction(spec) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const message = await this.orm.call("aic.home", spec.method, []);
            if (message) {
                this.notification.add(message, { type: "info" });
            }
            await this.load();
        } finally {
            this.state.busy = false;
        }
    }
    // To approve: the Approve key on a row (the record's own approve method, run as the user)
    async approveItem(item) {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            const message = await this.orm.call("aic.home", "approve_item", [item.model, item.res_id]);
            this.notification.add(message, { type: "success" });
            await this.load();
        } finally {
            this.state.busy = false;
        }
    }
    // To approve: Refuse opens a reason field in the row; the reason is required and goes to the record
    startRefuse(item) {
        this.state.refusing = item.model + item.res_id;
        this.state.refuseReason = "";
    }
    async refuseItem(item) {
        const reason = (this.state.refuseReason || "").trim();
        if (this.state.busy || !reason) {
            return;
        }
        this.state.busy = true;
        try {
            const message = await this.orm.call("aic.home", "refuse_item", [item.model, item.res_id, reason]);
            this.notification.add(message, { type: "info" });
            this.state.refusing = false;
            await this.load();
        } finally {
            this.state.busy = false;
        }
    }
    // ------------------------------------------------------------------ My week
    async setView(view) {
        this.state.view = view;
        if (view === "week") {
            await this.loadWeek();
        }
    }
    async loadWeek() {
        this.state.week = await this.orm.call("aic.home", "get_week_data", []);
    }
    barHeight(n) {
        const max = Math.max(1, ...this.state.week.days.map((d) => d.done + d.due));
        return `${Math.round((n / max) * 100)}%`;
    }
    dayTitle(d) {
        return _t("%(day)s %(date)s: %(done)s done, %(due)s still due", { day: d.label, date: d.date, done: d.done, due: d.due });
    }
    get weekBarsLabel() {
        return this.state.week.days.map((d) => this.dayTitle(d)).join("; ");
    }
    get teamMoreLabel() {
        return _t("And %s more.", this.state.week.team.more);
    }
    lastWeekLabel(n) {
        return _t("%s last week", n);
    }
    refresh() {
        this.state.loading = true;
        return this.state.view === "week" ? Promise.all([this.load(), this.loadWeek()]) : this.load();
    }

    // ------------------------------------------------------------------ Customise home
    // A working copy of the layout: switches and up / down keys change it, Done saves it for the person's
    // current role, Reset goes back to the role's own layout.
    openCustomise() {
        const layout = this.data.layout;
        const copy = (rows) => rows.map((row) => ({ ...row }));
        const apps = this.apps.map((app) => ({ key: "app:" + app.key, label: app.name, visible: !app.hidden }));
        this.state.customise = { tiles: copy(layout.tiles), panels: copy(layout.panels), sections: copy(layout.sections), apps };
        setTimeout(() => document.querySelector(".o_aic_cust input, .o_aic_cust button")?.focus(), 0);
    }
    closeCustomise() {
        this.state.customise = null;
        setTimeout(() => document.querySelector(".o_aic_cust_open")?.focus(), 0);
    }
    get customiseGroups() {
        return [["tiles", _t("Tiles")], ["panels", _t("Panels")], ["sections", _t("Sections")], ["apps", _t("Apps")]];
    }
    moveLabel(row, step) {
        return step < 0 ? _t("Move %s up", row.label) : _t("Move %s down", row.label);
    }
    toggleBlock(row) {
        row.visible = !row.visible;
    }
    moveBlock(group, index, step) {
        const rows = this.state.customise[group];
        const target = index + step;
        if (target < 0 || target >= rows.length) {
            return;
        }
        [rows[index], rows[target]] = [rows[target], rows[index]];
    }
    async saveCustomise() {
        const c = this.state.customise;
        const all = [...c.tiles, ...c.panels, ...c.sections, ...c.apps];
        this.state.busy = true;
        try {
            this.state.data = await this.orm.call("aic.home", "save_layout", [], {
                hidden: all.filter((row) => !row.visible).map((row) => row.key),
                order: [...c.tiles, ...c.panels, ...c.apps].map((row) => row.key),
            });
            this.closeCustomise();
        } finally {
            this.state.busy = false;
        }
    }
    async resetCustomise() {
        this.state.busy = true;
        try {
            this.state.data = await this.orm.call("aic.home", "reset_layout", []);
            this.closeCustomise();
            this.notification.add(_t("Home is back to the %s layout.", this.data.role_label), { type: "info" });
        } finally {
            this.state.busy = false;
        }
    }
    onCustomiseKey(ev) {
        if (ev.key === "Escape") {
            ev.stopPropagation();
            this.closeCustomise();
        }
    }
}

registry.category("actions").add("aic_home", AicHome);
