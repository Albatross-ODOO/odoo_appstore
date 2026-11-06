/** @odoo-module **/
// Workspace — swipe actions on phone cards (design M2). Swipe a kanban card left: it slides
// aside and shows up to three keys from the server (models/aic_swipe.py): Call, WhatsApp, Plan an
// activity, and the record's next step (Confirm a quotation, Won for an opportunity…). Tap a key, tap
// the card or swipe it back to close. Vertical scrolling is untouched (touch-action: pan-y), and the
// long press that selects cards still works: a swipe only starts on a clearly sideways move.
import { useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { ListRenderer } from "@web/views/list/list_renderer";

const KEY_WIDTH = 72;
const GAP = 8;
const START = 10;      // px before a move counts as a gesture
const OPEN_AT = 56;    // px of pull that opens the tray
let openCard = null;   // one tray open at a time

// ---------------------------------------------------------------------- shared by cards and rows
export async function loadSwipeKeys(env, record) {
    let a = {};
    try {
        a = await env.services.orm.call("aic.swipe", "get_actions", [record.resModel, record.resId]);
    } catch {
        a = {};
    }
    const keys = [];
    if (a.tel) {
        keys.push({ id: "call", label: _t("Call"), icon: "phone", href: a.tel, tone: "plum" });
    }
    if (a.whatsapp || a.whatsapp_url) {
        keys.push({ id: "whatsapp", label: _t("WhatsApp"), icon: "chat_bubble", tone: "plum-soft", data: a });
    }
    if (a.plan) {
        keys.push({ id: "plan", label: _t("Plan"), icon: "calendar_add_on", tone: "well" });
    }
    if (a.primary) {
        keys.push({ id: "primary", label: a.primary.label, icon: "check", tone: "brand", method: a.primary.method });
    }
    // at most three keys: the next step always, then Call, WhatsApp, Plan in that order
    while (keys.length > 3) {
        keys.splice(keys.length - 2, 1);
    }
    return keys;
}

export async function pressSwipeKey(env, key, ev, record, close) {
    const services = env.services;
    const reload = () => record.model.load();
    if (key.id === "call") {
        return close();    // the <a href="tel:…"> does the dialing
    }
    ev?.preventDefault();
    close();
    if (key.id === "whatsapp") {
        if (key.data.whatsapp) {
            return services.action.doAction(key.data.whatsapp, {
                additionalContext: { default_res_model: record.resModel, default_res_id: record.resId },
                onClose: reload,
            });
        }
        return window.open(key.data.whatsapp_url, "_blank", "noopener");
    }
    if (key.id === "plan") {
        await services["mail.store"].scheduleActivity(record.resModel, [record.resId]);
        return reload();
    }
    if (key.id === "primary") {
        return services.action.doActionButton({
            type: "object", name: key.method, resModel: record.resModel, resId: record.resId,
            resIds: [record.resId], context: record.context, onClose: reload,
        }).then(reload);
    }
}

patch(KanbanRecord.prototype, {
    setup() {
        super.setup(...arguments);
        this.aicSwipe = useState({ open: false, keys: [] });
        this.aicDrag = null;
        this.aicActions = null;   // promise of the server's keys, asked once per card
    },

    get aicSwipeAllowed() {
        const record = this.props.record;
        return Boolean(this.env.services.ui.isSmall && record && record.resId && !this.props.forceGlobalClick
            && !record.model.useSampleModel && !this.env.inDialog);
    },

    // ------------------------------------------------------------------ gesture
    onTouchStart(ev) {
        super.onTouchStart(...arguments);
        if (!this.aicSwipeAllowed || !ev?.touches || ev.touches.length !== 1) {
            return;
        }
        if (openCard && openCard !== this) {
            openCard.aicClose();
        }
        const t = ev.touches[0];
        this.aicDrag = { x0: t.clientX, y0: t.clientY, dx: 0, decided: false, sideways: false,
                           base: this.aicSwipe.open ? -this.aicTrayWidth() : 0 };
    },
    onTouchMoveOrCancel(ev) {
        super.onTouchMoveOrCancel(...arguments);
        const drag = this.aicDrag;
        if (!drag || !ev) {
            return;
        }
        if (ev.type === "touchcancel") {
            this.aicDrag = null;
            return this.aicSettle(this.aicSwipe.open);
        }
        const t = ev.touches?.[0];
        if (!t) {
            return;
        }
        const dx = t.clientX - drag.x0;
        const dy = t.clientY - drag.y0;
        if (!drag.decided) {
            if (Math.abs(dx) < START && Math.abs(dy) < START) {
                return;
            }
            drag.decided = true;
            drag.sideways = Math.abs(dx) > Math.abs(dy) * 1.4 && (dx < 0 || this.aicSwipe.open);
            if (drag.sideways && !this.aicActions) {
                this.aicActions = this.aicLoadKeys();
            }
        }
        if (!drag.sideways) {
            return;
        }
        drag.dx = dx;
        const limit = -(Math.max(this.aicTrayWidth(), 3 * KEY_WIDTH) + GAP + 24);
        const offset = Math.min(0, Math.max(limit, drag.base + dx));
        const el = this.rootRef.el;
        if (el) {
            el.classList.add("o_aic_swiping");
            el.style.transform = `translateX(${offset}px)`;
        }
    },
    async onTouchEnd(ev) {
        super.onTouchEnd(...arguments);
        const drag = this.aicDrag;
        this.aicDrag = null;
        if (!drag || !drag.sideways) {
            return;
        }
        this.aicJustSwiped = Date.now();
        const pulled = drag.base + drag.dx;
        if (pulled > -OPEN_AT) {
            return this.aicClose();
        }
        await this.aicActions;
        if (!this.aicSwipe.keys.length) {
            return this.aicClose();
        }
        this.aicSwipe.open = true;
        openCard = this;
        this.aicSettle(true);
    },
    onGlobalClick(ev) {
        // the click a swipe can leave behind, or a tap on a card whose tray is open, only closes it
        if ((this.aicJustSwiped && Date.now() - this.aicJustSwiped < 400) || this.aicSwipe.open) {
            if (!ev.target.closest(".o_aic_swipe_tray")) {
                ev.preventDefault?.();
                this.aicClose();
            }
            return;
        }
        return super.onGlobalClick(...arguments);
    },

    // ------------------------------------------------------------------ tray
    aicTrayWidth() {
        return this.aicSwipe.keys.length * KEY_WIDTH + GAP;
    },
    aicSettle(open) {
        const el = this.rootRef.el;
        if (!el) {
            return;
        }
        el.classList.remove("o_aic_swiping");
        el.style.transform = open ? `translateX(${-this.aicTrayWidth()}px)` : "";
    },
    aicClose() {
        this.aicSwipe.open = false;
        if (openCard === this) {
            openCard = null;
        }
        this.aicSettle(false);
    },
    async aicLoadKeys() {
        this.aicSwipe.keys = await loadSwipeKeys(this.env, this.props.record);
    },
    aicPress(key, ev) {
        return pressSwipeKey(this.env, key, ev, this.props.record, () => this.aicClose());
    },
});

// ---------------------------------------------------------------------- list rows (phones)
// The same gesture on list rows: the row slides left and the keys appear past its right edge.
patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.aicRowSwipe = useState({ open: null, keys: [] });   // open = the datapoint id of the open row
        this.aicRowDrag = null;
    },
    // Odoo's own row handlers first (long press selects), then the swipe
    aicRowTouchStart(record, ev) {
        this.onRowTouchStart(record, ev);
        this.aicRowStart(record, ev);
    },
    aicRowTouchMove(record, ev) {
        this.onRowTouchMove(record);
        this.aicRowMove(record, ev);
    },
    aicRowTouchEnd(record) {
        this.onRowTouchEnd(record);
        return this.aicRowEnd(record);
    },
    aicRowAllowed(record) {
        // the view's own list only: never the lines of a form (x2many), a dialog or sample data
        const list = this.props.list;
        return Boolean(this.env.services.ui.isSmall && record?.resId && list === list.model.root
            && !list.model.useSampleModel && !this.env.inDialog && !list.selection?.length && !record.isInEdition);
    },
    aicRowStart(record, ev) {
        if (!this.aicRowAllowed(record) || ev.touches?.length !== 1) {
            return;
        }
        if (this.aicRowSwipe.open && this.aicRowSwipe.open !== record.id) {
            this.aicRowClose();
        }
        const t = ev.touches[0];
        this.aicRowDrag = { record, row: ev.currentTarget, x0: t.clientX, y0: t.clientY, dx: 0, decided: false,
                              sideways: false, base: this.aicRowSwipe.open === record.id ? -this.aicRowWidth() : 0 };
    },
    aicRowMove(record, ev) {
        const drag = this.aicRowDrag;
        const t = ev.touches?.[0];
        if (!drag || drag.record !== record || !t) {
            return;
        }
        const dx = t.clientX - drag.x0;
        const dy = t.clientY - drag.y0;
        if (!drag.decided) {
            if (Math.abs(dx) < START && Math.abs(dy) < START) {
                return;
            }
            drag.decided = true;
            drag.sideways = Math.abs(dx) > Math.abs(dy) * 1.4 && (dx < 0 || this.aicRowSwipe.open === record.id);
            if (drag.sideways) {
                drag.keys = loadSwipeKeys(this.env, record);
            }
        }
        if (!drag.sideways) {
            return;
        }
        drag.dx = dx;
        const offset = Math.min(0, Math.max(-(3 * KEY_WIDTH + GAP + 24), drag.base + dx));
        drag.row.classList.add("o_aic_swiping");
        drag.row.style.transform = `translateX(${offset}px)`;
    },
    async aicRowEnd(record) {
        const drag = this.aicRowDrag;
        this.aicRowDrag = null;
        if (!drag || !drag.sideways) {
            return;
        }
        this.aicRowJustSwiped = Date.now();
        if (drag.base + drag.dx > -OPEN_AT) {
            return this.aicRowClose(drag.row);
        }
        const keys = await drag.keys;
        if (!keys.length) {
            return this.aicRowClose(drag.row);
        }
        Object.assign(this.aicRowSwipe, { open: record.id, keys });
        this.aicRowRow = drag.row;
        drag.row.classList.remove("o_aic_swiping");
        drag.row.style.transform = `translateX(${-this.aicRowWidth()}px)`;
    },
    aicRowWidth() {
        return this.aicRowSwipe.keys.length * KEY_WIDTH + GAP;
    },
    aicRowClose(row = this.aicRowRow) {
        this.aicRowSwipe.open = null;
        if (row) {
            row.classList.remove("o_aic_swiping");
            row.style.transform = "";
        }
        this.aicRowRow = null;
    },
    aicRowPress(record, key, ev) {
        return pressSwipeKey(this.env, key, ev, record, () => this.aicRowClose());
    },
    onClickCapture(record, ev) {
        // the click a swipe can leave behind, or a tap on a row whose tray is open, only closes it
        const fresh = this.aicRowJustSwiped && Date.now() - this.aicRowJustSwiped < 400;
        if ((fresh || this.aicRowSwipe.open) && !ev.target.closest(".o_aic_swipe_tray")) {
            ev.stopPropagation();
            ev.preventDefault();
            return this.aicRowClose();
        }
        return super.onClickCapture(...arguments);
    },
});
