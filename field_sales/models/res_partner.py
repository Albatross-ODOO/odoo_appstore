# -*- coding: utf-8 -*-

from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_field_lead = fields.Boolean(string='Is Field Lead', default=False, index=True)
    field_sales_visit_ids = fields.One2many('field.sales.visit', 'partner_id', string='Field Sales Visits')
