/** @odoo-module **/
// Workspace — the phone filter sheet (design M6): Odoo's own search menu, laid out as chips
// (search_sheet.scss) with a "Show results" key that closes it.
import { patch } from "@web/core/utils/patch";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";

patch(SearchBarMenu.prototype, {
    get aicSmall() {
        return this.env.services.ui.isSmall;
    },
    aicCloseSearch() {
        if (this.props.dropdownState?.close) {
            return this.props.dropdownState.close();
        }
        document.querySelector(".o_searchview_dropdown_toggler")?.click();
    },
});
