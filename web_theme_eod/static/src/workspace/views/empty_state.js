/** @odoo-module **/
// "Nothing yet": Odoo's empty state is a large illustration over the help text. Here it is one card: the help's
// first sentence as the headline, the rest as one muted line, and one action — New, which presses the view's own
// New button (so the view's create rules, quick create and dialogs apply). Views without a New button (reports,
// read-only lists) show no key (empty_state.scss).
import { patch } from "@web/core/utils/patch";
import { ActionHelper } from "@web/views/action_helper";

const NEW_BUTTONS = ".o_list_button_add, .o-kanban-button-new";

patch(ActionHelper.prototype, {
    aicCreate(ev) {
        const root = ev.target.closest(".o_view_controller") || document;
        const button = [...root.querySelectorAll(NEW_BUTTONS)].find((b) => !b.disabled);
        button?.click();
    },
});
