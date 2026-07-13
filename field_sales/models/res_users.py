# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    active_field_session_id = fields.Many2one(
        'field.sales.session', 
        string='Active Field Sales Session',
        compute='_compute_active_session'
    )

    def _compute_active_session(self):
        for user in self:
            active = self.env['field.sales.session'].search([
                ('user_id', '=', user.id),
                ('state', '=', 'checked_in')
            ], limit=1)
            user.active_field_session_id = active.id if active else False
