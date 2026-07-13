# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class FieldSalesVisit(models.Model):
    _name = 'field.sales.visit'
    _description = 'Field Sales Client Visit'
    _order = 'check_in_time desc'

    session_id = fields.Many2one('field.sales.session', string='Active Session', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string='Linked Lead/Prospect', index=True)

    company_name = fields.Char(string='Company Name', required=True)
    contact_name = fields.Char(string='Contact Person Name')
    phone = fields.Char(string='Phone Number', required=True)
    notes = fields.Text(string='Visit Notes')

    check_in_time = fields.Datetime(string='Check-In Time', default=fields.Datetime.now, readonly=True)
    check_out_time = fields.Datetime(string='Check-Out Time', readonly=True)

    latitude = fields.Float(string='Latitude', digits=(10, 7), readonly=True)
    longitude = fields.Float(string='Longitude', digits=(10, 7), readonly=True)
    accuracy = fields.Float(string='Accuracy (meters)', readonly=True)
    duration = fields.Float(string='Duration (Minutes)', compute='_compute_duration', store=True)
    visit_image = fields.Binary(string='Visit Photo', attachment=True, readonly=True)

    @api.depends('check_in_time', 'check_out_time')
    def _compute_duration(self):
        for record in self:
            if record.check_in_time and record.check_out_time:
                delta = record.check_out_time - record.check_in_time
                record.duration = delta.total_seconds() / 60.0
            else:
                record.duration = 0.0

    def action_complete_visit(self, latitude, longitude, accuracy, visit_image=False):
        self.ensure_one()
        self.write({
            'check_out_time': fields.Datetime.now(),
            'latitude': latitude,
            'longitude': longitude,
            'accuracy': accuracy,
            'visit_image': visit_image,
        })
        
        # Log coordinate in trajectory
        self.env['field.sales.location.log'].create({
            'session_id': self.session_id.id,
            'latitude': latitude,
            'longitude': longitude,
            'log_type': 'visit',
        })

        # Automate res.partner lead generation/updating
        partner = self._find_or_create_partner()
        self.write({'partner_id': partner.id})
        return True

    def _find_or_create_partner(self):
        self.ensure_one()
        Partner = self.env['res.partner']
        Category = self.env['res.partner.category']

        # Find or create "Field Lead" category tag
        tag = Category.search([('name', '=', 'Field Lead')], limit=1)
        if not tag:
            tag = Category.create({'name': 'Field Lead', 'color': 4}) # Color 4 is a nice blue/cyan

        # Search existing partner by phone or contact details
        existing_partner = Partner.search([
            ('phone', '=', self.phone)
        ], limit=1)

        if existing_partner:
            # Update existing partner with tags/flags
            existing_partner.write({
                'is_field_lead': True,
                'category_id': [(4, tag.id)],
            })
            return existing_partner
        else:
            # Create a brand new partner
            new_partner = Partner.create({
                'name': self.company_name,
                'phone': self.phone,
                'is_field_lead': True,
                'category_id': [(4, tag.id)],
                'comment': f"Created from Field Sales Visit by {self.session_id.user_id.name}.\nContact Person: {self.contact_name or ''}\nNotes: {self.notes or ''}",
            })
            # If contact name is given, create a contact under the company
            if self.contact_name:
                Partner.create({
                    'name': self.contact_name,
                    'parent_id': new_partner.id,
                    'type': 'contact',
                    'phone': self.phone,
                })
            return new_partner
