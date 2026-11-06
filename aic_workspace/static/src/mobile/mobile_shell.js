/** @odoo-module **/
// Workspace — app-like mobile shell: the bottom tab bar (Home · current app · + · Activities · Me,
// design M1 since 20.0.3.3.0), the grouped-kanban stage chips and the stage picker.
//
// An overlay component (registered in main_components, exactly like the left pane) so it
// NEVER touches the navbar or webclient templates. It renders only while the `ui` service
// reports `isSmall` (< 768px), which is the same breakpoint aic_theme/scss/mobile.scss
// keys off — so the desktop (and a tablet) is provably untouched.
//
// The tabs open Odoo's OWN navigation, restyled by the theme — nothing is redrawn:
//   Home       → the user's home action (Home when installed), else the "All Apps" drawer
//   App        → the drawer with the current app's sections (label + icon of the current app)
//   +          → the current screen's own primary "New" button (disabled when there is none)
//   Activities → the Core Focus queue when installed, else the activity menu of the top bar
//   Me         → the burger menu (user · companies · preferences · log out)   — burger_menu.js
import { Component, useEffect, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { stageStore } from "./stage_store";
import "./kanban_stage_patch"; // installs the KanbanController patch that feeds stageStore

export class AicMobileShell extends Component {
    static template = "aic_workspace.MobileShell";

    setup() {
        this.ui = useState(useService("ui"));
        // overlay: null | "stages"
        this.state = useState({ overlay: null, onForm: false, screen: "app", canCreate: false });
        this.action = useService("action");
        this.menu = useService("menu");
        // the grouped-kanban stage picker is driven by a reactive store the Kanban controller
        // feeds (real stages + server totals + a real domain filter) — see kanban_stage_patch.js
        this.stage = useState(stageStore);
        // mail store (for closing Discuss chat windows on navigation); guarded — may be absent
        this.mailStore = this.env.services["mail.store"];

        // body classes: the shell is on screen / a sheet is open / a record's form is on screen
        useEffect(() => {
            const b = document.body;
            b.classList.toggle("o_aic_mobile", this.active);
            b.classList.toggle("o_aic_m_locked", this.active && !!this.state.overlay);
            b.classList.toggle("o_aic_m_form", this.active && this.state.onForm);
        });

        // On ANY navigation: (1) close any open sheet; (2) close any Discuss chat window — on
        // mobile it's a full-screen fixed overlay that otherwise stays on top of the newly-opened
        // app and makes it look "stuck"; (3) clear leftover stage state; (4) note whether the
        // screen is a record's form (the "tab bar on a record" preference reads it).
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => {
            this.state.overlay = null;
            this.closeChatWindows();
            this.state.onForm = !!document.querySelector(".o_action_manager > .o_action.o_form_view");
            this.state.screen = document.querySelector(".o_action_manager .o_aic_home") ? "home"
                : document.querySelector(".o_action_manager .o_aic_focus_queue") ? "focus" : "app";
            this.state.canCreate = !!this.createButton;
            // the control panel renders just after this event: look again once it is there
            setTimeout(() => (this.state.canCreate = !!this.createButton), 400);
            setTimeout(() => {
                const hasGroupedKanban = document.querySelector(".o_kanban_view .o_kanban_renderer.o_kanban_grouped");
                if (!hasGroupedKanban && stageStore.active) {
                    stageStore.reset();
                }
            }, 350);
        });

    }

    get active() {
        return this.ui.isSmall;
    }

    // -- overlays ------------------------------------------------------------
    openOverlay(name) {
        this.state.overlay = this.state.overlay === name ? null : name;
    }
    closeOverlay() {
        this.state.overlay = null;
    }

    // -- the tabs: Odoo's own navigation ---------------------------------------
    get currentApp() {
        let app = null;
        try {
            app = this.menu.getCurrentApp();
        } catch {
            app = null;
        }
        // on Home itself the "current app" tab offers all apps instead of repeating Home
        if (!app || this.state.screen !== "app" || app.xmlid === "aic_home.menu_aic_home_root") {
            return null;
        }
        return app;
    }
    onAppTab() {
        return this.currentApp ? this.openMenu() : this.openApps();
    }
    get activityCount() {
        return this.mailStore?.activityCounter || 0;
    }
    get createButton() {
        // the screen's own primary "New"; on phones Odoo makes it a small menu button (New ▾), which
        // is fine: pressing it opens Odoo's New menu. Never the split "More" toggle.
        return document.querySelector(
            ".o_action_manager .o_control_panel .o_control_panel_main_buttons button.btn-primary:not(.dropdown-toggle-split):not([disabled])"
        );
    }
    async openHome() {
        this.closeOverlay();
        if (user.homeActionId) {
            try {
                await this.action.doAction(user.homeActionId, { clearBreadcrumbs: true });
                return;
            } catch {
                // the home action is gone or not allowed: fall back to the apps drawer
            }
        }
        this.openApps();
    }
    onCreate() {
        this.closeOverlay();
        this.createButton?.click();
    }
    async openActivities() {
        this.closeOverlay();
        try {
            await this.action.doAction("aic_home.action_aic_focus", { clearBreadcrumbs: true });
        } catch {
            this.openActivity();   // Home not installed: Odoo's activity menu
        }
    }
    openApps() {
        this.closeOverlay();
        this.env.bus.trigger("AIC:APP-DRAWER", "apps");
    }
    openMenu() {
        this.closeOverlay();
        this.env.bus.trigger("AIC:APP-DRAWER", "menu");
    }
    openActivity() {
        this.closeOverlay();
        // Odoo's own activity menu (top bar), not a copy of it
        const icon = document.querySelector('.o_menu_systray .oi[data-icon="schedule"]');
        const btn = icon && icon.closest("button");
        if (btn) {
            btn.click();
        }
    }
    openAccount() {
        this.closeOverlay();
        this.env.bus.trigger("AIC:BURGER");
    }

    // -- stage picker (grouped kanban) ---------------------------------------
    // All data + filtering comes from the reactive stageStore, fed by the Kanban controller
    // (kanban_stage_patch.js). Selecting a stage applies a real search domain server-side.
    get showStagePicker() {
        // 20.0.3.3.0: the stage chips at the top of the kanban (kanban_stage_chips.js) replace the
        // floating picker; the sheet stays reachable from them for long stage lists
        return false;
    }
    get stages() {
        return this.stage.groups;
    }
    isStageSelected(value) {
        return this.stage.selected === value;
    }
    selectStage(value) {
        if (this.stage.apply) {
            // undefined from the "All" button -> clear the filter
            this.stage.apply(value === undefined ? null : value);
        }
        this.closeOverlay();
    }
    get currentStageLabel() {
        if (this.stage.selected === null) {
            return "All stages";
        }
        const g = this.stage.groups.find((s) => s.value === this.stage.selected);
        return g ? g.label : "Stage";
    }
    get isStageFiltered() {
        return this.stage.selected !== null;
    }

    // -- navigation ----------------------------------------------------------
    closeChatWindows() {
        // close any open Discuss chat window so it can't cover the view we navigate to
        try {
            this.mailStore?.chatHub?.closeAll();
        } catch {
            // mail not loaded / API changed — ignore
        }
    }

}

registry.category("main_components").add("AicMobileShell", { Component: AicMobileShell });
