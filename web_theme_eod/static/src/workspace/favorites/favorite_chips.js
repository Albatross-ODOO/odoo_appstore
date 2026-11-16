/** @odoo-module **/
// Core: saved favourites as one-click chips under the control panel. A chip applies the favourite
// (and shows it as active, in the "you are here" colour); clicking it again removes it.
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";
import { useBus } from "@web/core/utils/hooks";
import { render } from "@web/owl2/utils";

const MAX_CHIPS = 8;

patch(ControlPanel.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.env.searchModel) {
            useBus(this.env.searchModel, "update", () => render(this));
        }
    },
    get aicFavorites() {
        const sm = this.env.searchModel;
        if (!sm || !sm.getSearchItems) {
            return [];
        }
        try {
            return sm.getSearchItems((item) => item.type === "favorite").slice(0, MAX_CHIPS);
        } catch {
            return [];
        }
    },
    aicToggleFavorite(item) {
        this.env.searchModel.toggleSearchItem(item.id);
    },
});
