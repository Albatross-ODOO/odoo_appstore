/** @odoo-module **/
// Inventory in plain words (no dependency on Inventory: both widgets are put into the forms by the web client):
// - a delivery or internal transfer waiting for stock starts with what is still missing — each product, how many of
//   how many, and when Odoo expects it;
// - a storable product shows its stock in one strip (on hand, to deliver, incoming, forecast, minimum, can make);
// - a manufacturing order shows its routing as steps (done, in progress, to do, blocked);
// - the backorder dialog says what a backorder would carry ("Still missing: 20 Coils, 3 Desks") and asks the
//   question in those terms; Odoo's two generic paragraphs give way to it (stock_summary.scss), its keys stay.
import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const { DateTime } = luxon;

export class AicPickingMissing extends Component {
    static template = "aic_workspace.PickingMissing";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ rows: false });
        onWillStart(() => this.load(this.props.record));
        onWillUpdateProps((next) => {
            if (next.record.resId !== this.props.record.resId || next.record.data.state !== this.props.record.data.state) {
                return this.load(next.record);
            }
        });
    }
    async load(record) {
        // a summary is a help, never a blocker: if it cannot be made, the transfer opens as usual
        try {
            this.state.rows = record.resId ? await this.orm.silent.call("aic.stock.summary", "picking_missing", [record.resId]) : false;
        } catch {
            this.state.rows = false;
        }
    }
    line(row) {
        return _t("%(missing)s of %(demand)s %(uom)s not available yet", row);
    }
    expected(row) {
        return row.expected ? _t("expected %(date)s", { date: DateTime.fromISO(row.expected).toLocaleString({ day: "numeric", month: "short" }) }) : "";
    }
}

export class AicBackorderSummary extends Component {
    static template = "aic_workspace.BackorderSummary";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ data: false });
        onWillStart(async () => {
            const ids = this.props.record.data.pick_ids?.currentIds || [];
            try {
                this.state.data = ids.length ? await this.orm.silent.call("aic.stock.summary", "backorder_summary", [ids]) : false;
            } catch {
                this.state.data = false;
            }
        });
    }
    get missingText() {
        const items = this.state.data.items.map((i) => i.label);
        const more = this.state.data.more ? _t(" and %(n)s more", { n: this.state.data.more }) : "";
        return _t("Still missing: %(items)s%(more)s.", { items: items.join(", "), more });
    }
    get question() {
        return this.state.data.outgoing
            ? _t("Create a backorder to send them later, or close the delivery without them?")
            : _t("Create a backorder to process them later, or close the transfer without them?");
    }
}

// a storable product's stock in one strip under its smart buttons
export class AicProductStrip extends Component {
    static template = "aic_workspace.ProductStrip";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ chips: false });
        onWillStart(() => this.load(this.props.record));
        onWillUpdateProps((next) => {
            if (next.record.resId !== this.props.record.resId) {
                return this.load(next.record);
            }
        });
    }
    async load(record) {
        try {
            this.state.chips = record.resId
                ? await this.orm.silent.call("aic.stock.summary", "product_strip", [record.resModel, record.resId])
                : false;
        } catch {
            this.state.chips = false;
        }
    }
}

// a manufacturing order's routing as steps: done, in progress, to do, blocked
export class AicMoSteps extends Component {
    static template = "aic_workspace.MoSteps";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ data: false });
        onWillStart(() => this.load(this.props.record));
        onWillUpdateProps((next) => {
            if (next.record.resId !== this.props.record.resId || next.record.data.state !== this.props.record.data.state) {
                return this.load(next.record);
            }
        });
    }
    async load(record) {
        try {
            this.state.data = record.resId ? await this.orm.silent.call("aic.stock.summary", "mo_steps", [record.resId]) : false;
        } catch {
            this.state.data = false;
        }
    }
    get progress() {
        return _t("%(done)s of %(total)s steps done", this.state.data);
    }
}

registry.category("view_widgets").add("aic_picking_missing", { component: AicPickingMissing });
registry.category("view_widgets").add("aic_mo_steps", { component: AicMoSteps });
registry.category("view_widgets").add("aic_product_strip", { component: AicProductStrip });
registry.category("view_widgets").add("aic_backorder_summary", { component: AicBackorderSummary });

function inject(xmlDoc, name, where) {
    if (xmlDoc.querySelector(`widget[name=${name}]`)) {
        return;
    }
    const widget = xmlDoc.ownerDocument.createElement("widget");
    widget.setAttribute("name", name);
    if (where === "sheet") {
        const sheet = xmlDoc.querySelector("sheet");
        if (!sheet) {
            return;
        }
        const box = sheet.querySelector(":scope > div[name=button_box]");
        sheet.insertBefore(widget, box ? box.nextSibling : sheet.firstChild);
    } else {
        xmlDoc.insertBefore(widget, xmlDoc.firstChild);
    }
}

patch(FormArchParser.prototype, {
    parse(xmlDoc, models, modelName) {
        if (modelName === "product.template" || modelName === "product.product") {
            inject(xmlDoc, "aic_product_strip", "sheet");
        } else if (modelName === "mrp.production") {
            inject(xmlDoc, "aic_mo_steps", "sheet");
        } else if (modelName === "stock.picking") {
            inject(xmlDoc, "aic_picking_missing", "sheet");
        } else if (modelName === "stock.backorder.confirmation") {
            inject(xmlDoc, "aic_backorder_summary", "top");
        }
        return super.parse(...arguments);
    },
});
