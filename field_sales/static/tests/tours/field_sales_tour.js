/** @odoo-module */

import { registry } from "@web/core/registry";

/* Browser checks: every view of the module is opened once and the OWL kiosk /
 * Leaflet route map are exercised. Data comes from tests/test_field_sales_ui.py
 * (rep "Field Rep UI" with a checked-in session, one completed visit at
 * "Acme Corporation" and one visit in progress). */

const step = (label) => [
    { trigger: `.kiosk-modal-card .nm-step-active .nm-step-kicker:contains('${label}')` },
    { trigger: ".kiosk-modal-footer .nm-btn--primary:not([disabled])", run: "click" },
];

registry.category("web_tour.tours").add("field_sales_kiosk_tour", {
    url: "/odoo/action-field_sales.action_field_sales_kiosk_client_action",
    steps: () => [
        { trigger: ".field-sales-kiosk-container .nm-chip--live" },
        { trigger: ".field-sales-kiosk-container .nm-kpi-value:contains('1')" },
        { trigger: ".nm-active-visit .fa-map-pin" },
        { trigger: ".nm-actions .nm-btn--danger[disabled] .fa-sign-out" },
        // open the progressive "check-out client visit" form
        { trigger: ".nm-actions .nm-btn--success .fa-check-square-o", run: "click" },
        { trigger: ".kiosk-modal-card .nm-progress-text:contains('STEP 1 / 8')" },
        { trigger: ".kiosk-modal-card .nm-step-active input.nm-input", run: "edit Acme" },
        { trigger: ".kiosk-modal-card .nm-suggest-item--create .fa-plus" },
        { trigger: ".kiosk-modal-card .nm-suggest-item:not(.nm-suggest-item--create):contains('Acme Corporation')", run: "click" },
        { trigger: ".kiosk-modal-card .nm-linked .fa-check-circle" },
        { trigger: ".kiosk-modal-footer .nm-btn--primary:not([disabled])", run: "click" },
        ...step("Contact person"),
        ...step("Phone"),
        ...step("Email"),
        { trigger: ".kiosk-modal-card .nm-step-active .nm-linked .fa-link" },
        ...step("Odoo records"),
        ...step("Visit notes"),
        { trigger: ".kiosk-modal-card .nm-step-active .nm-step-kicker:contains('Visit photo')" },
        { trigger: ".kiosk-modal-card .nm-photo-empty .fa-camera" },
        // jump back to a completed step, then close the form
        { trigger: ".kiosk-modal-card .nm-step-done:contains('Client') .fa-pencil", run: "click" },
        { trigger: ".kiosk-modal-card .nm-progress-text:contains('STEP 1 / 8')" },
        { trigger: ".kiosk-modal-header .nm-btn--icon .fa-times", run: "click" },
        { trigger: ".field-sales-kiosk-container:not(:has(.kiosk-modal-card))" },
    ],
});

registry.category("web_tour.tours").add("field_sales_session_tour", {
    url: "/odoo/action-field_sales.action_field_sales_session",
    steps: () => [
        { trigger: ".o_list_view .o_data_row:contains('Field Rep UI') .o_data_cell:first", run: "click" },
        { trigger: ".o_form_view .o_field_widget[name='location_verification']" },
        { trigger: ".o_form_view .o_notebook .nav-link:contains('Client Visits')", run: "click" },
        { trigger: ".o_form_view .o_field_widget[name='visit_ids'] .o_data_row:contains('Acme Corporation')" },
        { trigger: ".o_form_view .o_notebook .nav-link:contains('Route Logs')", run: "click" },
        { trigger: ".o_form_view .o_field_widget[name='location_log_ids'] .o_data_row:contains('Check-In')" },
        { trigger: ".o_form_view .o_notebook .nav-link:contains('Route Map')", run: "click" },
        // Leaflet is loaded (window.L) and drew the trajectory polyline + markers from the record
        { trigger: ".o_session_route_map .leaflet-container path.leaflet-interactive" },
        { trigger: ".o_session_route_map .leaflet-control-attribution:contains('OpenStreetMap')" },
    ],
});

registry.category("web_tour.tours").add("field_sales_visit_tour", {
    url: "/odoo/action-field_sales.action_field_sales_visit",
    steps: () => [
        { trigger: ".o_list_view .o_data_row:contains('Acme Corporation') .o_data_cell:first", run: "click" },
        { trigger: ".o_form_view .o_field_widget[name='company_name'] input" },
        { trigger: ".o_form_view .o_field_widget[name='lead_id']:contains('Lead from Visit')" },
        { trigger: ".o_form_view .o_field_widget[name='user_id']" },
        // the breadcrumb names the visit after its client, not "field.sales.visit,<id>"
        { trigger: ".o_breadcrumb .active:contains('Acme Corporation')" },
    ],
});

registry.category("web_tour.tours").add("field_sales_prospects_tour", {
    url: "/odoo/action-field_sales.action_field_sales_leads",
    steps: () => [
        { trigger: ".o_list_view .o_data_row:contains('Acme Corporation') .o_data_cell:first", run: "click" },
        { trigger: ".o_form_view .o_notebook .nav-link:contains('Field Sales Visits')", run: "click" },
        { trigger: ".o_form_view .o_field_widget[name='field_sales_visit_ids'] .o_data_row" },
        { trigger: ".o_form_view .o_field_widget[name='is_field_lead'] input:checked" },
    ],
});
