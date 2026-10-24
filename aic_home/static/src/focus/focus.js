/** @odoo-module **/
// Core Focus queue: the user's due activities, one record at a time, with one-key actions.
//   D done · F done + follow up in 2 days · P done + plan next (Odoo dialog)
//   S snooze to tomorrow · W snooze a week · → or N skip · ← back · O open the record
//   Ctrl/⌘ + Enter in the note box = done
import { Component, onMounted, onWillStart, onWillUnmount, proxy, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

export class AicFocus extends Component {
    static template = "aic_home.Focus";
    props = useProps({ ...standardActionServiceProps });

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = proxy({
            loading: true, busy: false,
            ids: [], index: 0, card: null,
            due: 0, doneToday: 0, startDone: 0,
            models: [], resModel: false, feedback: "",
        });
        this.onKey = this.onKey.bind(this);
        onWillStart(() => this.loadQueue());
        onMounted(() => window.addEventListener("keydown", this.onKey));
        onWillUnmount(() => window.removeEventListener("keydown", this.onKey));
    }

    // ------------------------------------------------------------------ data
    async loadQueue(resModel = this.state.resModel) {
        const q = await this.orm.call("aic.focus", "get_queue", [resModel || false]);
        Object.assign(this.state, {
            ids: q.ids, index: 0, due: q.due, doneToday: q.done_today, models: q.models,
            resModel: q.res_model, loading: false,
        });
        if (!this.state.startDone) {
            this.state.startDone = q.done_today;
        }
        await this.loadCard();
    }
    async loadCard() {
        this.state.feedback = "";
        while (this.state.index < this.state.ids.length) {
            const card = await this.orm.call("aic.focus", "get_card", [this.state.ids[this.state.index]]);
            if (!card.gone) {
                this.state.card = card;
                return;
            }
            this.state.ids.splice(this.state.index, 1);   // done or moved elsewhere meanwhile
        }
        this.state.card = null;
    }
    applyCounts(counts) {
        this.state.due = counts.due;
        this.state.doneToday = counts.done_today;
    }

    // ------------------------------------------------------------------ derived
    get progress() {
        const total = this.state.doneToday + this.state.due;
        return total ? Math.round((100 * this.state.doneToday) / total) : 100;
    }
    get progressStyle() {
        return `width: ${this.progress}%`;
    }
    // whole sentences with placeholders, so translators can order the words for their language
    get countLabel() {
        return _t("%(done)s done today · %(due)s still due", { done: this.state.doneToday, due: this.state.due });
    }
    get clearLabel() {
        return this.state.resModel
            ? _t("Nothing is due or overdue for this type. %s done today.", this.state.doneToday)
            : _t("Nothing is due or overdue. %s done today.", this.state.doneToday);
    }
    get otherLabel() {
        return _t("+%s other activities", this.state.card?.other_activities || 0);
    }
    get lateClass() {
        const late = this.state.card?.activity.late || 0;
        return late > 0 ? "o_aic_focus_late" : "o_aic_focus_today";
    }

    // ------------------------------------------------------------------ actions
    async run(fn) {
        if (this.state.busy || !this.state.card) {
            return;
        }
        this.state.busy = true;
        try {
            await fn();
        } finally {
            this.state.busy = false;
        }
    }
    removeCurrentAndContinue() {
        this.state.ids.splice(this.state.index, 1);
        return this.loadCard();
    }
    done(followUpDays = 0) {
        return this.run(async () => {
            const counts = await this.orm.call("aic.focus", "mark_done", [
                this.state.card.activity.id, this.state.feedback || false, followUpDays,
            ]);
            this.applyCounts(counts);
            this.notification.add(
                followUpDays ? _t("Done. Follow-up planned in %s days.", followUpDays) : _t("Done."),
                { type: "success" }
            );
            await this.removeCurrentAndContinue();
        });
    }
    doneAndPlan() {
        return this.run(async () => {
            const action = await this.orm.call("aic.focus", "done_and_plan", [
                this.state.card.activity.id, this.state.feedback || false,
            ]);
            await this.action.doAction(action, {
                onClose: async () => {
                    this.applyCounts(await this.orm.call("aic.focus", "get_counts", []));
                    await this.removeCurrentAndContinue();
                },
            });
        });
    }
    snooze(days) {
        return this.run(async () => {
            this.applyCounts(await this.orm.call("aic.focus", "snooze", [this.state.card.activity.id, days]));
            this.notification.add(days === 1 ? _t("Moved to tomorrow.") : _t("Moved %s days ahead.", days), { type: "info" });
            await this.removeCurrentAndContinue();
        });
    }
    skip(step = 1) {
        if (this.state.busy) {
            return;
        }
        const next = this.state.index + step;
        if (next < 0 || next > this.state.ids.length) {
            return;
        }
        this.state.index = next;
        return this.loadCard();
    }
    openRecord() {
        const rec = this.state.card?.record;
        if (!rec || !rec.model || !rec.id) {
            return;
        }
        return this.action.doAction({
            type: "ir.actions.act_window", res_model: rec.model, res_id: rec.id,
            views: [[false, "form"]], target: "current",
        });
    }
    filter(model) {
        this.state.loading = true;
        return this.loadQueue(model || false);
    }
    onFeedback(ev) {
        this.state.feedback = ev.target.value;
    }

    onKey(ev) {
        const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(ev.target.tagName) || ev.target.isContentEditable;
        if (typing) {
            if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") {
                ev.preventDefault();
                this.done();
            }
            return;
        }
        if (ev.ctrlKey || ev.metaKey || ev.altKey || document.querySelector(".modal")) {
            return;
        }
        const map = {
            d: () => this.done(), f: () => this.done(2), p: () => this.doneAndPlan(),
            s: () => this.snooze(1), w: () => this.snooze(7),
            n: () => this.skip(1), ArrowRight: () => this.skip(1), ArrowLeft: () => this.skip(-1),
            o: () => this.openRecord(),
        };
        const handler = map[ev.key] || map[ev.key.toLowerCase?.()];
        if (handler) {
            ev.preventDefault();
            handler();
        }
    }
}

registry.category("actions").add("aic_focus", AicFocus);
