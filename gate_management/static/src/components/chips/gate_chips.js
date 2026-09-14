/** @odoo-module */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/** Selection field drawn as large tappable chips (or a segmented control with options.segment). */
export class GateChips extends Component {
    static template = "gate_management.GateChips";
    static props = {
        ...standardFieldProps,
        exclude: { type: Array, optional: true },
        icons: { type: Object, optional: true },
        labels: { type: Object, optional: true },
        segment: { type: Boolean, optional: true },
    };

    get choices() {
        const selection = this.props.record.fields[this.props.name].selection || [];
        const exclude = this.props.exclude || [];
        return selection
            .filter(([value]) => !exclude.includes(value))
            .map(([value, label]) => ({
                value,
                label: (this.props.labels || {})[value] || label,
                icon: (this.props.icons || {})[value],
            }));
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    select(value) {
        if (this.props.readonly || value === this.value) {
            return;
        }
        this.props.record.update({ [this.props.name]: value });
    }
}

export const gateChips = {
    component: GateChips,
    supportedTypes: ["selection"],
    extractProps: ({ options }) => ({
        exclude: options.exclude,
        icons: options.icons,
        labels: options.labels,
        segment: Boolean(options.segment),
    }),
};

registry.category("fields").add("gate_chips", gateChips);
