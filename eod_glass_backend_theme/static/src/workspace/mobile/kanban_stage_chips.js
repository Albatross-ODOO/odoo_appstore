/** @odoo-module **/
// Core (design M4): on phones, a grouped kanban shows one stage at a time, picked from a row of
// stage chips at the top. The chips read the stage store the Kanban controller feeds
// (kanban_stage_patch.js) and call its apply(), which filters server-side, so only the chosen
// stage's records load. Tapping the active chip again shows every stage.
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { stageStore } from "./stage_store";

patch(KanbanRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.aicStage = stageStore;
        this.aicUi = useService("ui");
    },
    get aicShowStageChips() {
        return Boolean(this.aicUi.isSmall && this.props.list.isGrouped && this.aicStage.active
            && this.aicStage.apply && this.aicStage.groups.length > 1);
    },
    aicStageChipClass(value) {
        return { o_active: this.aicStage.selected === value };
    },
    aicPickStage(value) {
        const next = this.aicStage.selected === value ? null : value;
        this.aicStage.apply?.(next);
    },
});
