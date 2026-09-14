/** @odoo-module */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { goHome, loadGateFonts } from "../utils";

/** <widget name="gate_home"/> — the Home button on every Gate Desk page. Never saves the form. */
export class GateHomeButton extends Component {
    static template = "gate_management.GateHomeButton";
    static props = { ...standardWidgetProps };

    setup() {
        this.action = useService("action");
        loadGateFonts();
    }

    async goHome() {
        // A guard leaving a half-filled page abandons it: never auto-save a draft on the way home.
        if (this.props.record && this.props.record.isNew) {
            await this.props.record.discard();
        }
        await goHome(this.action);
    }
}

registry.category("view_widgets").add("gate_home", { component: GateHomeButton });
