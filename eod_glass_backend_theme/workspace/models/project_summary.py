# -*- coding: utf-8 -*-
"""A task as a visit, for the technician who goes on site (no dependency on Project: asked by the web client only
on a task): the customer, the address with a map link, a call key, the deadline and how far the sub-tasks are."""
import re
from urllib.parse import quote_plus

from odoo import api, fields, models


class AicProjectSummary(models.AbstractModel):
    _name = "aic.project.summary"
    _description = "Core: task visit"

    @api.model
    def task_visit(self, task_id):
        if "project.task" not in self.env:
            return False
        task = self.env["project.task"].browse(int(task_id)).exists()
        if not task or not task.has_access("read") or task.is_closed or not task.partner_id:
            return False
        partner = task.partner_id
        address = ", ".join(filter(None, [partner.street, partner.street2, partner.zip and partner.city and f"{partner.zip} {partner.city}" or partner.city,
                                          partner.state_id.name, partner.country_id.name]))
        phone = partner.phone or (partner.mobile if "mobile" in partner._fields else "") or ""
        digits = re.sub(r"[^\d+]", "", phone)
        return {
            "customer": partner.display_name,
            "address": address,
            "map": f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}" if address else False,
            "phone": phone,
            "tel": f"tel:{digits}" if digits else False,
            "deadline": fields.Datetime.to_string(task.date_deadline) if task.date_deadline else False,
            "subtasks": task.subtask_count, "subtasks_done": task.closed_subtask_count,
        }
