/** @odoo-module */

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { gateToast, loadGateFonts, nowHM } from "../utils";

const PAGES = {
    walkin: "gate_management.action_gate_entry_kiosk_visitor",
    verify: "gate_management.action_gate_verify_kiosk",
    worker: "gate_management.action_gate_worker_kiosk",
    schedule: "gate_management.action_gate_entry_schedule",
    entries: "gate_management.action_gate_entries",
};

/** Gate Desk — the guard's home page. One client action, no menu hunting. */
export class GateDeskHome extends Component {
    static template = "gate_management.GateDeskHome";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, data: null, gone: {} });
        loadGateFonts();
        onWillStart(() => this.load());
        onMounted(() => {
            this.timer = setInterval(() => this.load(), 60000);
        });
        onWillUnmount(() => clearInterval(this.timer));
    }

    async load() {
        try {
            this.state.data = await this.orm.call("gate.entry", "gate_desk_data", []);
        } finally {
            this.state.loading = false;
        }
    }

    open(page, extra = {}) {
        return this.action.doAction(PAGES[page], extra);
    }

    openEntries(filter) {
        return this.action.doAction(PAGES.entries, { additionalContext: { gd_filter: filter } });
    }

    openStat(which) {
        return this.openEntries({ inside: "inside", expected: "scheduled", exited: "exited" }[which] || "all");
    }

    openEntry(row) {
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "gate.entry",
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async checkOut(row) {
        this.state.gone[row.id] = true;
        try {
            await this.orm.call("gate.entry", "action_exit", [[row.id]]);
            gateToast(_t("%s checked out · %s", row.title, nowHM()));
        } finally {
            await this.load();
            delete this.state.gone[row.id];
        }
    }

    avClass(row) {
        return row.overdue ? "gd-av-warn" : "gd-av-in";
    }

    initials(row) {
        if (row.type === "vehicle") {
            return (row.title || "").replace(/\s+/g, "").slice(0, 2).toUpperCase();
        }
        return (row.title || "?").split(" ").map((s) => s[0]).join("").slice(0, 2).toUpperCase();
    }
}

registry.category("actions").add("gate_management.gate_desk_home", GateDeskHome);
