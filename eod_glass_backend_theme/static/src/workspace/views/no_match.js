/** @odoo-module **/
// Empty views: Odoo shows the action's "create your first…" help whenever a list or kanban has no row (and a
// grouped kanban "No <group> yet, let's create some!"), even when records exist and only the search matched
// nothing. When the user has typed a search term (a field facet), the view says so instead — "Nothing matches
// your search", the term, and one key that removes the typed terms (filters such as "My Opportunities" stay).
// Without a typed term Odoo's own help is unchanged.
import { ActionHelper } from "@web/views/action_helper";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { patch } from "@web/core/utils/patch";

const noMatch = {
    get aicTypedFacets() {
        const sm = this.env.searchModel;
        return sm ? sm.facets.filter((f) => f.type === "field") : [];
    },
    get aicNoMatch() {
        return this.aicTypedFacets.length > 0;
    },
    get aicTerms() {
        return this.aicTypedFacets.flatMap((f) => f.values).join(", ");
    },
    aicClearTyped() {
        for (const facet of this.aicTypedFacets) {
            this.env.searchModel.deactivateGroup(facet.groupId);
        }
    },
};

patch(ActionHelper.prototype, noMatch);
patch(KanbanRenderer.prototype, noMatch);
