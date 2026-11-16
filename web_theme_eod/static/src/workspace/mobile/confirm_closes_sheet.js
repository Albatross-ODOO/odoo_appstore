/** @odoo-module **/
// Phones: a record's secondary actions sit in Odoo's bottom sheet (the "More" dropdown of the action
// bar). A button with a confirmation (Cancel on a quotation, Reset to Draft…) opens its dialog BEFORE
// Odoo closes the dropdown (ViewButton closes it in `beforeExecute`, after the user confirms), so the
// sheet stayed open behind the dialog, and still after "No, go back". Close it first; the confirmation
// and the action run exactly as before (Odoo already runs them after the button is gone).
import { patch } from "@web/core/utils/patch";
import { ViewButton } from "@web/views/view_button/view_button";

patch(ViewButton.prototype, {
    onClick(ev, newWindow) {
        if (this.clickParams.confirm && !this.props.onClick) {
            this.dropdownControl.close();
        }
        return super.onClick(ev, newWindow);
    },
});
