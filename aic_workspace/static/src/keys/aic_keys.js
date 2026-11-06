/** @odoo-module **/
// Keyboard: j / k move to the next / previous record (a form: the pager; a list or kanban: the rows or cards,
// Enter opens), and ? opens a sheet of the shortcuts (also in the user menu). Keys only count when nobody is
// typing and no dialog is open; Odoo's own Alt shortcuts and Ctrl+K are untouched.
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { isMacOS } from "@web/core/browser/feature_detection";

export class AicKeysDialog extends Component {
    static template = "aic_workspace.KeysDialog";
    static components = { Dialog };
    static props = { close: Function };

    get groups() {
        const ctrl = isMacOS() ? "⌘" : "Ctrl";
        return [
            { title: _t("Anywhere"), keys: [
                [[ctrl, "K"], _t("Search apps, menus and records")],
                [["?"], _t("This list of shortcuts")],
                [["Alt"], _t("Hold to see the letter of every button")],
                [["Esc"], _t("Close a dialog or a panel")],
            ] },
            { title: _t("Lists and kanbans"), keys: [
                [["j"], _t("Next row or card")],
                [["k"], _t("Previous row or card")],
                [["Enter"], _t("Open it")],
                [["Alt", "C"], _t("New record")],
            ] },
            { title: _t("A record"), keys: [
                [["j"], _t("Next record")],
                [["k"], _t("Previous record")],
                [["Alt", "S"], _t("Save")],
                [["Alt", "J"], _t("Discard changes")],
            ] },
        ];
    }
}

function typing(target) {
    return Boolean(target?.closest?.("input, textarea, select, [contenteditable=''], [contenteditable='true']"));
}

function visible(el) {
    return el && el.offsetParent !== null;
}

/** the rows / cards of the view on screen: a list's data rows or a kanban's records */
function items() {
    const scope = [...document.querySelectorAll(".o_action_manager .o_view_controller")].filter(visible).pop();
    if (!scope) {
        return { scope: null, list: [] };
    }
    const list = [...scope.querySelectorAll(".o_list_renderer .o_data_row, .o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)")].filter(visible);
    return { scope, list };
}

function focusItem(el) {
    const target = el.matches(".o_data_row") ? el.querySelector("td.o_data_cell") || el : el;
    if (!target.hasAttribute("tabindex")) {
        target.setAttribute("tabindex", "-1");
    }
    target.focus();
    target.scrollIntoView({ block: "nearest" });
}

function step(dir) {
    const { scope, list } = items();
    if (!scope) {
        return false;
    }
    if (scope.querySelector(".o_form_view") || scope.matches(".o_form_view")) {
        const button = [...document.querySelectorAll(`.o_control_panel ${dir > 0 ? ".o_pager_next" : ".o_pager_previous"}`)].filter(visible).pop();
        if (button && !button.disabled) {
            button.click();
            return true;
        }
        return false;
    }
    if (!list.length) {
        return false;
    }
    const current = list.findIndex((el) => el.contains(document.activeElement));
    const next = current === -1 ? (dir > 0 ? 0 : list.length - 1) : Math.min(list.length - 1, Math.max(0, current + dir));
    focusItem(list[next]);
    return true;
}

export const aicKeysService = {
    dependencies: ["dialog"],
    start(env, { dialog }) {
        let sheetOpen = false;
        const openSheet = () => {
            if (sheetOpen) {
                return;
            }
            sheetOpen = true;
            dialog.add(AicKeysDialog, {}, { onClose: () => (sheetOpen = false) });
        };
        browser.addEventListener("keydown", (ev) => {
            if (ev.ctrlKey || ev.metaKey || ev.altKey || ev.defaultPrevented || typing(ev.target)) {
                return;
            }
            if (document.querySelector(".modal, .o_command_palette, .o-overlay-item .dropdown-menu")) {
                return;
            }
            if (ev.key === "?") {
                ev.preventDefault();
                openSheet();
            } else if ((ev.key === "j" || ev.key === "k") && step(ev.key === "j" ? 1 : -1)) {
                ev.preventDefault();
            }
        });
        return { openSheet };
    },
};
registry.category("services").add("aic_keys", aicKeysService);

registry.category("user_menuitems").add("aic_keys", (env) => ({
    type: "item",
    id: "aic_keys",
    description: _t("Keyboard shortcuts"),
    hide: env.isSmall,
    callback: () => env.services.aic_keys.openSheet(),
    sequence: 46,
}), { sequence: 46 });
