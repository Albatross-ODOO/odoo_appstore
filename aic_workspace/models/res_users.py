# -*- coding: utf-8 -*-
from odoo import api, fields, models

# Preferences a user changes about themselves (the Core panel writes them with the user's own
# rights): Odoo 20 marks such fields `user_writeable=True` (19's SELF_WRITEABLE_FIELDS is gone).


class ResUsers(models.Model):
    _inherit = "res.users"

    aic_nav = fields.Selection(
        [("top", "Odoo top bar only"), ("side", "Left pane, expanded"), ("mini", "Left pane, icons")],
        string="Navigation",
        default="top",
        help="The Odoo top bar is always there. A left pane can be shown next to it, "
             "expanded or collapsed to icons; the ☰ button in the top bar toggles it at any time.",
        user_writeable=True,
    )
    aic_split = fields.Boolean(
        string="Split Form View",
        default=False,
        help="Open records from a list or kanban in a panel beside the list "
             "instead of navigating to the form.",
        user_writeable=True,
    )
    aic_split_side = fields.Selection(
        [("right", "Right of the list"), ("bottom", "Below the list")],
        string="Split panel position",
        default="right",
        user_writeable=True,
    )
    aic_split_chatter = fields.Selection(
        [("float", "Floats automatically"), ("docked", "Docked below the form")],
        string="Chatter in the split view",
        default="float",
        help="Floating: when a record opens in the split panel its chatter pops out into a "
             "movable, resizable window that follows the selected record. Docked: the chatter "
             "stays below the form inside the panel (it can still be floated with a click).",
        user_writeable=True,
    )
    aic_chatter = fields.Selection(
        [("right", "Right of the form"), ("bottom", "Below the form")],
        string="Chatter position",
        default="right",
        user_writeable=True,
    )
    # phones only: the Apps · Menu · Activity · Account tab bar while a record's form is open
    aic_m_tabbar = fields.Selection(
        [("keep", "Kept under the record's actions"), ("hide", "Hidden while a record is open")],
        string="Phone: tab bar on a record",
        default="keep",
        help="On a phone, a record's form has its own bar of actions at the bottom. Keep the "
             "app tab bar under it (two bars), or hide the tab bar while a record is open — "
             "the Back key returns to the list, like a mail app.",
        user_writeable=True,
    )

    # desktop: a record header with more than four buttons keeps three (primaries first) and puts
    # the rest under "⋯", as Odoo does on phones
    aic_header_compact = fields.Boolean(
        string="Compact record header",
        default=True,
        help="When a record has more than four buttons in its header, show the main ones and put "
             "the rest under ⋯. Off: every button stays in the header, as in stock Odoo.",
        user_writeable=True,
    )

    # desktop: how much fits on screen; compact tightens list rows, form fields and kanban cards (phones keep their
    # touch-sized rows)
    aic_density = fields.Selection(
        [("comfortable", "Comfortable"), ("compact", "Compact")],
        string="Density",
        default="comfortable",
        help="Compact fits more rows and fields on a desktop screen. Phones keep their touch-sized rows.",
        user_writeable=True,
    )

    # looks with translucent panes (EOD): reduced turns the panes nearly opaque and stops the blur — easier to
    # read for some people, and lighter on older phones. The system's "reduce transparency" setting does the same.
    aic_transparency = fields.Selection(
        [("full", "Full"), ("reduce", "Reduced")],
        string="Transparency",
        default="full",
        help="Reduced: panes are nearly opaque and nothing behind them is blurred. Only looks with translucent "
             "panes (EOD) use it.",
        user_writeable=True,
    )

    def _aic_prefs(self):
        """Preferences as sent to the web client (session_info)."""
        self.ensure_one()
        return {
            "nav": self.aic_nav or "top",
            "split": bool(self.aic_split),
            "split_side": self.aic_split_side or "right",
            "split_chatter": self.aic_split_chatter or "float",
            "chatter": self.aic_chatter or "right",
            "m_tabbar": self.aic_m_tabbar or "keep",
            "header_compact": bool(self.aic_header_compact),
            "density": self.aic_density or "comfortable",
            "transparency": self.aic_transparency or "full",
            # Odoo's own choice (mail): notifications by email or in Odoo's inbox; shared users are email only
            "notify": self.notification_type if "notification_type" in self._fields and not self.share else False,
        }

    @api.model
    def aic_my_profile_action(self):
        """The current user's own employee record (org chart, resume, time off when installed): the full one for HR
        officers, the public profile for everyone else."""
        employee = self.env.user.employee_id if "employee_id" in self.env.user._fields else False
        if not employee:
            return self.action_get()
        # people without HR rights see the public profile (Odoo hides the private one from them)
        model = "hr.employee" if self.env.user.has_group("hr.group_hr_user") else "hr.employee.public"
        return {
            "type": "ir.actions.act_window", "res_model": model, "res_id": employee.id,
            "views": [[False, "form"]], "name": employee.name, "target": "current",
        }
