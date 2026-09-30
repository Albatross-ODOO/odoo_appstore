/** @odoo-module */

import { Component, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/** Selection field drawn as large tappable chips (or a segmented control with options.segment).
 *  options.icons maps a value to a Material Symbols name (Odoo 20 icon set), e.g. {'visitor': 'person'}. */
export class GateChips extends Component {
    static template = "gate_management.GateChips";
    // Owl 3: props are declared through useProps (static props is ignored)
    props = useProps({
        ...standardFieldProps,
        exclude: t.array().optional(),
        icons: t.object().optional(),
        labels: t.object().optional(),
        segment: t.boolean().optional(),
    });

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
