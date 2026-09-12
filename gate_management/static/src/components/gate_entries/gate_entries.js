/** @odoo-module */

import { Component, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { goHome, loadGateFonts } from "../utils";

const FILTERS = [
    { key: "all", label: "All" },
    { key: "inside", label: "Inside" },
    { key: "scheduled", label: "Scheduled" },
    { key: "exited", label: "Exited" },
    { key: "vehicle", label: "Vehicles" },
    { key: "material", label: "Material" },
];

/** Entries — today's gate movements as Gate Desk rows; a row opens the native Odoo form (the audit surface). */
export class GateEntries extends Component {
    static template = "gate_management.GateEntries";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.filters = FILTERS;
        this.searchRef = useRef("search");
        const ctx = (this.props.action && this.props.action.context) || {};
        this.state = useState({
            filter: FILTERS.some((f) => f.key === ctx.gd_filter) ? ctx.gd_filter : "all",
            term: "", showSearch: false, rows: [], counts: {}, gate: "", loading: true,
        });
        loadGateFonts();
        onWillStart(() => this.load());
        onWillUnmount(() => clearTimeout(this.searchTimer));
    }

    goHome() {
        goHome(this.action);
    }

    async load() {
        const data = await this.orm.call("gate.entry", "gate_entries_data", [this.state.filter, this.state.term]);
        this.state.rows = data.rows;
        this.state.counts = data.counts;
        this.state.gate = data.gate;
        this.state.loading = false;
    }

    setFilter(key) {
        this.state.filter = key;
        this.load();
    }

    toggleSearch() {
        this.state.showSearch = !this.state.showSearch;
        if (!this.state.showSearch && this.state.term) {
            this.state.term = "";
            this.load();
        } else if (this.state.showSearch) {
            setTimeout(() => this.searchRef.el && this.searchRef.el.focus(), 50);
        }
    }

    onSearch(ev) {
        this.state.term = ev.target.value;
        clearTimeout(this.searchTimer);
        this.searchTimer = setTimeout(() => this.load(), 250);
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

    rowClass(row) {
        if (row.state === "entered") {
            return row.overdue ? "gd-row-break" : "gd-row-in";
        }
        if (row.state === "exited" || row.state === "cancel") {
            return "gd-row-out";
        }
        return "gd-row-sch";
    }

    pillClass(row) {
        if (row.state === "entered") {
            return row.overdue ? "gd-pill-brk" : "gd-pill-in";
        }
        if (row.state === "exited" || row.state === "cancel") {
            return "gd-pill-out";
        }
        return "gd-pill-gold";
    }

    avClass(row) {
        if (row.state === "entered") {
            return row.overdue ? "gd-av-warn" : "gd-av-in";
        }
        return row.state === "exited" || row.state === "cancel" ? "gd-av-out" : "";
    }

    initials(row) {
        if (row.type === "vehicle") {
            return (row.title || "").replace(/\s+/g, "").slice(0, 2).toUpperCase();
        }
        return (row.title || "?").split(" ").map((s) => s[0]).join("").slice(0, 2).toUpperCase();
    }
}

registry.category("actions").add("gate_management.entries", GateEntries);
