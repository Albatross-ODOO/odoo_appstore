/** @odoo-module */

import { registry } from "@web/core/registry";

const home = () => [
    { trigger: ".gd-app .gd-ico[title='Gate Desk']", run: "click" },
    { trigger: ".gd-app .gd-title:contains('Gate Desk')" },
];
const homeFromForm = () => [
    { trigger: ".o_gate_kiosk .gd-ico[title='Gate Desk']", run: "click" },
    { trigger: ".gd-app .gd-title:contains('Gate Desk')" },
];

registry.category("web_tour.tours").add("gate_desk_tour", {
    url: "/odoo/action-gate_management.action_gate_desk_home",
    steps: () => [
        { trigger: ".gd-app .gd-title:contains('Gate Desk')" },
        { trigger: ".gd-stats .gd-stat.gd-stat-in .gd-n" },

        // ---- Worker Attendance: check-in, break, break over
        { trigger: ".gd-tile:contains('Worker Attendance')", run: "click" },
        { trigger: ".gd-app .gd-title:contains('Worker Attendance')" },
        { trigger: ".gd-row:contains('Rakesh Patel') .gd-btn:contains('Check-In')", run: "click" },
        { trigger: ".gd-row:contains('Rakesh Patel') .gd-btn.gd-morph:contains('Check-Out')" },
        { trigger: ".gd-row:contains('Rakesh Patel') .gd-pill-in" },
        { trigger: ".gd-row:contains('Rakesh Patel') .gd-btn:contains('Break')", run: "click" },
        { trigger: ".gd-row:contains('Rakesh Patel') .gd-btn:contains('Break over')" },
        { trigger: ".gd-allbreak .gd-btn:contains('Break over')", run: "click" },
        { trigger: ".gd-row:contains('Rakesh Patel') .gd-pill-in" },
        ...home(),

        // ---- Walk-In: material entry (no photo needed)
        { trigger: ".gd-tile:contains('Walk-In Entry')", run: "click" },
        { trigger: ".o_gate_kiosk .gd-title:contains('Walk-In Entry')" },
        { trigger: ".gd-chip:contains('Vehicle')", run: "click" },
        { trigger: ".gd-chip[aria-pressed='true']:contains('Vehicle')" },
        { trigger: ".gd-chip:contains('Material')", run: "click" },
        { trigger: ".o_field_widget[name='material_name'] input", run: "edit 40 bags cement" },
        { trigger: ".gd-seg button:contains('Inward')" },
        { trigger: ".gd-btn:contains('Confirm Check-In')", run: "click" },
        { trigger: ".o_gate_kiosk .o_field_badge:contains('Draft')" },
        ...homeFromForm(),
        { trigger: ".gd-rows .gd-row:contains('40 bags cement')" },

        // ---- Entries page: filters + search, row opens the native form
        { trigger: ".gd-sect .gd-link:contains('See all')", run: "click" },
        { trigger: ".gd-app .gd-title:contains('Entries')" },
        { trigger: ".gd-ftab:contains('Material')", run: "click" },
        { trigger: ".gd-row-compact:contains('40 bags cement') .gd-pill:contains('Inside')" },
        { trigger: ".gd-ftab:contains('Exited')", run: "click" },
        { trigger: ".gd-rows .gd-empty, .gd-rows .gd-row-compact" },
        { trigger: ".gd-ftab:contains('All')", run: "click" },
        { trigger: ".gd-row-compact:contains('40 bags cement')", run: "click" },
        { trigger: ".o_form_view .o_field_widget[name='material_name']" },
        { trigger: ".o_breadcrumb .breadcrumb-item:contains('Entries')", run: "click" },
        { trigger: ".gd-app .gd-title:contains('Entries')" },
        ...home(),

        // ---- Verify: keypad with a known code
        { trigger: ".gd-tile:contains('Verify Invitation')", run: "click" },
        { trigger: ".o_gate_kiosk .gd-title:contains('Verify Invitation')" },
        { trigger: ".gd-key:contains('4')", run: "click" },
        { trigger: ".gd-key:contains('8')", run: "click" },
        { trigger: ".gd-key:contains('2')", run: "click" },
        { trigger: ".gd-key:contains('9')", run: "click" },
        { trigger: ".gd-key:contains('1')", run: "click" },
        { trigger: ".gd-key:contains('7')", run: "click" },
        { trigger: ".gd-match:contains('Meera Joshi')" },
        { trigger: ".gd-btn:contains('Back')", run: "click" },
        { trigger: ".gd-otp" },
        ...homeFromForm(),

        // ---- Schedule page opens
        { trigger: ".gd-tile:contains('Schedule Visit')", run: "click" },
        { trigger: ".o_gate_kiosk .gd-title:contains('Schedule Visit')" },
        { trigger: ".o_field_widget[name='visitor_name'] input", run: "edit Tour Visitor" },
        ...homeFromForm(),
    ],
});
