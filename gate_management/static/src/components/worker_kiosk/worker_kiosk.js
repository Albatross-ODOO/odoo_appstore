/** @odoo-module */

import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { gateToast, goHome, loadGateFonts, nowHM } from "../utils";

const ACTIONS = {
    in: { method: "action_check_in", state: "inside", msg: _t("%s checked in · %s") },
    out: { method: "action_check_out", state: "outside", msg: _t("%s checked out · %s") },
    break: { method: "action_start_break", state: "break", msg: _t("%s on break · %s") },
    resume: { method: "action_end_break", state: "inside", msg: _t("%s back from break · %s") },
};

/** Worker Attendance — Inside / On break / Outside, per-row actions and a common break. */
export class WorkerKiosk extends Component {
    static template = "gate_management.WorkerKiosk";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            term: "", tab: "inside", rows: [], counts: { inside: 0, break: 0, outside: 0 },
            loading: true, confirm: false, busy: false, morph: {}, gone: {}, clock: nowHM(),
        });
        loadGateFonts();
        onWillStart(() => this.load());
        this.clockTimer = setInterval(() => (this.state.clock = nowHM()), 15000);
        onWillUnmount(() => {
            clearInterval(this.clockTimer);
            clearTimeout(this.moveTimer);
            clearTimeout(this.searchTimer);
        });
    }

    goHome() {
        goHome(this.action);
    }

    async load() {
        const data = await this.orm.call("gate.worker", "kiosk_data", [this.state.term]);
        this.state.rows = data.rows.map((r) => ({ ...r, list: r.state }));
        this.state.counts = data.counts;
        this.state.loading = false;
        this.state.gone = {};
        this.state.morph = {};
    }

    async refreshCounts() {
        try {
            const data = await this.orm.call("gate.worker", "kiosk_data", [this.state.term, 1]);
            this.state.counts = data.counts;
        } catch (err) {
            console.warn("count refresh failed", err);
        }
    }

    onSearch(ev) {
        this.state.term = ev.target.value;
        clearTimeout(this.searchTimer);
        this.searchTimer = setTimeout(() => this.load(), 250);
    }

    /** Rows stay in the list they were shown in until their slide-out finishes. */
    rowsFor(state) {
        return this.state.rows.filter((r) => r.list === state);
    }

    initials(name) {
        return (name || "?").split(" ").map((s) => s[0]).join("").slice(0, 2).toUpperCase();
    }

    /** One press: the button morphs in place into the next action, then the row slides to its new list. */
    async act(row, key) {
        if (this.state.busy) {
            return;
        }
        const spec = ACTIONS[key];
        this.state.busy = true;
        try {
            await this.orm.call("gate.worker", spec.method, [[row.id]]);
        } catch (err) {
            this.state.busy = false;
            throw err;
        }
        const now = nowHM();
        row.state = spec.state;
        if (key === "in") {
            row.since = now;
        }
        if (key === "break") {
            row.break_since = now;
        }
        this.state.morph[row.id] = true;
        gateToast(_t(spec.msg, row.name, now));
        this.state.busy = false;
        await this.refreshCounts();
        clearTimeout(this.moveTimer);
        this.moveTimer = setTimeout(() => {
            this.state.gone[row.id] = true;
            setTimeout(() => this.load(), 380);
        }, 1500);
    }

    askBreakAll() {
        this.state.confirm = true;
    }

    async breakAll() {
        this.state.confirm = false;
        const n = await this.orm.call("gate.worker", "action_break_all", []);
        gateToast(_t("%s workers on break · %s", n, nowHM()));
        this.state.tab = "break";
        await this.load();
    }

    async breakOverAll() {
        const n = await this.orm.call("gate.worker", "action_break_over_all", []);
        gateToast(_t("Break over · %s workers back inside", n));
        this.state.tab = "inside";
        await this.load();
    }
}

registry.category("actions").add("gate_management.worker_kiosk", WorkerKiosk);
