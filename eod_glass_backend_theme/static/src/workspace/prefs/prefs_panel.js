/** @odoo-module **/
// Workspace — "Theme preferences" slide-out panel (the visual settings from the
// design preview). Opened from the user menu. Every control writes a per-user preference
// through the aic_prefs service.
import { Component, reactive, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// reactive singleton so the user-menu item can open the panel and the panel reacts
export const aicPanelState = reactive({ open: false });

export class AicPrefsPanel extends Component {
    static template = "aic_workspace.PrefsPanel";

    setup() {
        this.svc = useService("aic_prefs");
        // proxies: what the template reads re-renders the panel when it changes
        this.prefs = useState(this.svc.prefs);
        this.state = useState(aicPanelState);
    }

    close() {
        this.state.open = false;
    }
    setNav(nav) {
        this.svc.set({ nav });
    }
    get keepExpanded() {
        return this.prefs.nav === "side";
    }
    toggleKeepExpanded() {
        if (this.prefs.nav === "top") {
            return;
        }
        this.svc.set({ nav: this.prefs.nav === "side" ? "mini" : "side" });
    }
    setDensity(density) {
        this.svc.set({ density });
    }
    get translucentLook() {
        return document.body.classList.contains("o_aic_skin_eod");
    }
    setTransparency(transparency) {
        this.svc.set({ transparency });
    }
    setNotify(notify) {
        this.svc.set({ notify });
    }
    toggleHeaderCompact() {
        this.svc.set({ header_compact: !this.prefs.header_compact });
    }
    toggleSplit() {
        this.svc.set({ split: !this.prefs.split });
    }
    setSplitChatter(v) {
        this.svc.set({ split_chatter: v });
    }
    setSplitSide(side) {
        this.svc.set({ split_side: side });
    }
    setChatter(pos) {
        this.svc.set({ chatter: pos });
    }
    setTabbar(v) {
        this.svc.set({ m_tabbar: v });
    }
    get mode() {
        return this.svc.mode;
    }
    setMode(mode) {
        if (mode !== this.mode) {
            this.svc.setMode(mode);
        }
    }
}

registry.category("main_components").add("AicPrefsPanel", { Component: AicPrefsPanel });
