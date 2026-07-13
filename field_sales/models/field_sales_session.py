# -*- coding: utf-8 -*-

# pyrefly: ignore [missing-import]
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FieldSalesSession(models.Model):
    _name = 'field.sales.session'
    _description = 'Field Sales Session'
    _order = 'date desc, check_in_time desc'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='Salesperson', required=True, default=lambda self: self.env.user, index=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('checked_in', 'Checked In'),
        ('completed', 'Completed')
    ], string='Status', required=True, default='draft', index=True)

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    check_in_time = fields.Datetime(string='Check-In Time', readonly=True)
    check_out_time = fields.Datetime(string='Check-Out Time', readonly=True)

    check_in_latitude = fields.Float(string='Check-In Latitude', digits=(10, 7), readonly=True)
    check_in_longitude = fields.Float(string='Check-In Longitude', digits=(10, 7), readonly=True)
    check_out_latitude = fields.Float(string='Check-Out Latitude', digits=(10, 7), readonly=True)
    check_out_longitude = fields.Float(string='Check-Out Longitude', digits=(10, 7), readonly=True)

    selfie_image = fields.Binary(string='Selfie Verification', attachment=True, readonly=True)
    checkout_selfie_image = fields.Binary(string='Checkout Selfie Verification', attachment=True, readonly=True)

    location_verification = fields.Selection([
        ('pending', 'Pending Check-Out'),
        ('same', 'Same Location'),
        ('changed', 'Location Changed'),
    ], string='Location Verification', compute='_compute_location_verification', store=True, default='pending')

    visit_ids = fields.One2many('field.sales.visit', 'session_id', string='Visits')
    location_log_ids = fields.One2many('field.sales.location.log', 'session_id', string='Route Trajectory')

    check_in_map_link = fields.Char(string='Check-In Location Link', compute='_compute_map_links')
    check_out_map_link = fields.Char(string='Check-Out Location Link', compute='_compute_map_links')

    total_visits = fields.Integer(string='Total Visits', compute='_compute_metrics', store=True)
    productive_visits = fields.Integer(string='Productive Visits', compute='_compute_metrics', store=True)

    @api.depends('check_in_latitude', 'check_in_longitude', 'check_out_latitude', 'check_out_longitude', 'state')
    def _compute_location_verification(self):
        import math
        for record in self:
            if record.state != 'completed':
                record.location_verification = 'pending'
                continue
            
            if not (record.check_in_latitude and record.check_in_longitude and 
                    record.check_out_latitude and record.check_out_longitude):
                record.location_verification = 'changed'
                continue

            # Calculate distance using Haversine
            lat1, lon1 = record.check_in_latitude, record.check_in_longitude
            lat2, lon2 = record.check_out_latitude, record.check_out_longitude
            
            R = 6371008.8  # Earth radius in meters
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            
            a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = R * c
            
            # Threshold: 200 meters (allowance for typical GPS inaccuracies in urban environments)
            if distance <= 200:
                record.location_verification = 'same'
            else:
                record.location_verification = 'changed'

    @api.depends('check_in_latitude', 'check_in_longitude', 'check_out_latitude', 'check_out_longitude')
    def _compute_map_links(self):
        for record in self:
            if record.check_in_latitude and record.check_in_longitude:
                record.check_in_map_link = f"https://www.google.com/maps/search/?api=1&query={record.check_in_latitude},{record.check_in_longitude}"
            else:
                record.check_in_map_link = False
            if record.check_out_latitude and record.check_out_longitude:
                record.check_out_map_link = f"https://www.google.com/maps/search/?api=1&query={record.check_out_latitude},{record.check_out_longitude}"
            else:
                record.check_out_map_link = False

    @api.depends('user_id', 'date')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.user_id.name} - {record.date}"

    @api.depends('visit_ids')
    def _compute_metrics(self):
        for record in self:
            record.total_visits = len(record.visit_ids)
            record.productive_visits = len(record.visit_ids.filtered(lambda v: v.partner_id))

    @api.constrains('user_id', 'state')
    def _check_active_session(self):
        for record in self:
            if record.state == 'checked_in':
                active_sessions = self.search([
                    ('user_id', '=', record.user_id.id),
                    ('state', '=', 'checked_in'),
                    ('id', '!=', record.id)
                ])
                if active_sessions:
                    raise ValidationError(_("You cannot start a new session because you already have an active check-in."))

    def action_check_in(self, latitude, longitude, selfie_image):
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_("Session is not in New state."))
        
        self.write({
            'state': 'checked_in',
            'check_in_time': fields.Datetime.now(),
            'check_in_latitude': latitude,
            'check_in_longitude': longitude,
            'selfie_image': selfie_image,
        })
        # Log first coordinate in routing table
        self.env['field.sales.location.log'].create({
            'session_id': self.id,
            'latitude': latitude,
            'longitude': longitude,
            'log_type': 'check_in',
        })
        return True

    def action_check_out(self, latitude, longitude, checkout_selfie_image=False):
        self.ensure_one()
        if self.state != 'checked_in':
            raise ValidationError(_("Session is not checked in."))
        if not self.visit_ids:
            raise ValidationError(_("You must log at least one client visit before checking out."))
        
        self.write({
            'state': 'completed',
            'check_out_time': fields.Datetime.now(),
            'check_out_latitude': latitude,
            'check_out_longitude': longitude,
            'checkout_selfie_image': checkout_selfie_image,
        })
        # Log end coordinate in routing table
        self.env['field.sales.location.log'].create({
            'session_id': self.id,
            'latitude': latitude,
            'longitude': longitude,
            'log_type': 'check_out',
        })
        return True

    @api.model
    def action_kiosk_check_in(self, latitude, longitude, selfie_image):
        # Create a session in draft first
        session = self.create({
            'user_id': self.env.user.id,
            'date': fields.Date.context_today(self),
        })
        session.action_check_in(latitude, longitude, selfie_image)
        return {
            'session_id': session.id,
            'state': session.state,
        }

    def action_kiosk_check_out(self, latitude, longitude, checkout_selfie_image=False):
        self.ensure_one()
        self.action_check_out(latitude, longitude, checkout_selfie_image)
        return True

    def action_log_visit(self, company_name, contact_name, phone, notes, latitude, longitude, accuracy, visit_image=False, check_in_time=False):
        self.ensure_one()
        visit_vals = {
            'session_id': self.id,
            'company_name': company_name,
            'contact_name': contact_name,
            'phone': phone,
            'notes': notes,
        }
        if check_in_time:
            # clean up ISO string: '2026-07-10T12:00:00.000Z' -> '2026-07-10 12:00:00'
            formatted_time = check_in_time.replace('T', ' ').replace('Z', '')
            if '.' in formatted_time:
                formatted_time = formatted_time.split('.')[0]
            visit_vals['check_in_time'] = fields.Datetime.to_datetime(formatted_time)

        visit = self.env['field.sales.visit'].create(visit_vals)
        visit.action_complete_visit(latitude, longitude, accuracy, visit_image)
        return visit.id

