# -*- coding: utf-8 -*-

from odoo import models, fields

class FieldSalesLocationLog(models.Model):
    _name = 'field.sales.location.log'
    _description = 'Field Sales Location Log'
    _order = 'timestamp asc'

    session_id = fields.Many2one('field.sales.session', string='Session', required=True, ondelete='cascade', index=True)
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, readonly=True)
    latitude = fields.Float(string='Latitude', digits=(10, 7), required=True, readonly=True)
    longitude = fields.Float(string='Longitude', digits=(10, 7), required=True, readonly=True)
    log_type = fields.Selection([
        ('ping', 'Interval Ping'),
        ('check_in', 'Check-In'),
        ('check_out', 'Check-Out'),
        ('visit', 'Client Visit')
    ], string='Event Type', default='ping', required=True, readonly=True)
