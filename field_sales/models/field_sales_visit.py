# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class FieldSalesVisit(models.Model):
    _name = 'field.sales.visit'
    _description = 'Field Sales Client Visit'
    _order = 'check_in_time desc'

    state = fields.Selection([
        ('draft', 'New'),
        ('in_progress', 'Checked In'),
        ('completed', 'Completed')
    ], string='Status', default='draft', required=True, index=True)

    session_id = fields.Many2one('field.sales.session', string='Active Session', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Salesperson', related='session_id.user_id', store=True, index=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Linked Lead/Prospect', index=True)
    lead_id = fields.Many2one('crm.lead', string='Linked Lead/Opportunity', index=True)

    company_name = fields.Char(string='Company Name', required=True)
    contact_name = fields.Char(string='Contact Person Name')
    phone = fields.Char(string='Phone Number', required=True)
    email = fields.Char(string='Email')
    notes = fields.Text(string='Visit Notes')

    create_contact_bool = fields.Boolean(string='Create Contact?', default=False)
    create_lead_bool = fields.Boolean(string='Create Lead?', default=False)

    check_in_time = fields.Datetime(string='Check-In Time', default=fields.Datetime.now, readonly=True)
    check_out_time = fields.Datetime(string='Check-Out Time', readonly=True)

    latitude = fields.Float(string='Latitude', digits=(10, 7), readonly=True)
    longitude = fields.Float(string='Longitude', digits=(10, 7), readonly=True)
    accuracy = fields.Float(string='Accuracy (meters)', readonly=True)
    duration = fields.Float(string='Duration (Minutes)', compute='_compute_duration', store=True)
    visit_image = fields.Binary(string='Visit Photo', attachment=True, readonly=True)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            partner = self.partner_id
            if partner.is_company:
                self.company_name = partner.name
                self.contact_name = False
            elif partner.parent_id:
                self.company_name = partner.parent_id.name
                self.contact_name = partner.name
            else:
                self.company_name = partner.name
                self.contact_name = partner.name

            self.phone = partner.phone or ''
            self.email = partner.email or ''

    @api.constrains('create_contact_bool', 'create_lead_bool', 'company_name', 'contact_name', 'phone', 'email')
    def _check_mandatory_fields(self):
        for record in self:
            if record.create_contact_bool or record.create_lead_bool:
                if not (record.company_name or record.contact_name):
                    raise ValidationError(_("Contact Name or Company Name is required when 'Create Contact?' or 'Create Lead?' is checked."))
                if not (record.phone or record.email):
                    raise ValidationError(_("Phone Number or Email is required when 'Create Contact?' or 'Create Lead?' is checked."))

    @api.depends('check_in_time', 'check_out_time')
    def _compute_duration(self):
        for record in self:
            if record.check_in_time and record.check_out_time:
                delta = record.check_out_time - record.check_in_time
                record.duration = max(0.0, delta.total_seconds() / 60.0)
            else:
                record.duration = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._process_contact_and_lead_creation()
        return records

    def write(self, vals):
        res = super().write(vals)
        trigger_fields = {'create_contact_bool', 'create_lead_bool', 'company_name', 'contact_name', 'phone', 'email', 'notes'}
        if any(field in vals for field in trigger_fields):
            for record in self:
                record._process_contact_and_lead_creation()
        return res

    def action_start_visit(self, latitude=False, longitude=False, accuracy=False):
        self.ensure_one()
        self.write({
            'state': 'in_progress',
            'check_in_time': fields.Datetime.now(),
            'latitude': latitude or 0.0,
            'longitude': longitude or 0.0,
            'accuracy': accuracy or 0.0,
        })
        if latitude and longitude:
            self.env['field.sales.location.log'].create({
                'session_id': self.session_id.id,
                'latitude': latitude,
                'longitude': longitude,
                'log_type': 'visit',
            })
        return True

    def action_complete_visit(self, latitude=False, longitude=False, accuracy=False, visit_image=False, vals=False):
        self.ensure_one()
        update_dict = {
            'state': 'completed',
            'check_out_time': fields.Datetime.now(),
        }
        if latitude:
            update_dict['latitude'] = latitude
        if longitude:
            update_dict['longitude'] = longitude
        if accuracy:
            update_dict['accuracy'] = accuracy
        if visit_image:
            update_dict['visit_image'] = visit_image
        if vals and isinstance(vals, dict):
            update_dict.update(vals)

        self.write(update_dict)

        if not self.check_in_time:
            self.check_in_time = fields.Datetime.now()

        # Process contact and lead creation according to boolean flags
        self._process_contact_and_lead_creation()
        return True

    def _process_contact_and_lead_creation(self):
        self.ensure_one()
        # Step 1: Create or link res.partner if create_contact_bool is checked
        if self.create_contact_bool and not self.partner_id:
            partner = self._find_or_create_partner()
            if partner:
                self.partner_id = partner.id

        # Step 2: Create crm.lead if create_lead_bool is checked
        if self.create_lead_bool and not self.lead_id:
            lead = self._create_lead()
            if lead:
                self.lead_id = lead.id

    def _get_formatted_phone(self):
        """Phone number used to match and create records. Hook for local formatting rules."""
        self.ensure_one()
        return self.phone

    def _get_salesperson_id(self):
        """Salesperson who generated the record from the field: the session owner, else the current user."""
        self.ensure_one()
        return (self.session_id and self.session_id.user_id.id) or self.env.uid

    def _find_or_create_partner(self):
        self.ensure_one()
        # sudo: field reps may not have rights to create contacts/tags themselves
        Partner = self.env['res.partner'].sudo()
        Category = self.env['res.partner.category'].sudo()
        salesperson_id = self._get_salesperson_id()
        phone = self._get_formatted_phone()

        # Find or create "Field Lead" category tag
        tag = Category.search([('name', '=', 'Field Lead')], limit=1)
        if not tag:
            tag = Category.create({'name': 'Field Lead', 'color': 4})

        # Duplicate prevention check by Email or Phone Number
        domain = []
        if self.email and phone:
            domain = ['|', ('email', '=', self.email), ('phone', '=', phone)]
        elif self.email:
            domain = [('email', '=', self.email)]
        elif phone:
            domain = [('phone', '=', phone)]

        existing_partner = Partner.search(domain, limit=1) if domain else Partner.browse()

        if existing_partner:
            # Update existing partner with tag and salesperson
            partner_vals = {
                'is_field_lead': True,
                'category_id': [(4, tag.id)],
            }
            if not existing_partner.user_id:
                partner_vals['user_id'] = salesperson_id
            existing_partner.write(partner_vals)
            return existing_partner
        else:
            # Create a brand new partner
            partner_name = self.company_name or self.contact_name or "Field Lead"
            new_partner = Partner.create({
                'name': partner_name,
                'phone': phone,
                'email': self.email,
                'user_id': salesperson_id,
                'is_field_lead': True,
                'category_id': [(4, tag.id)],
                'comment': f"Created from Field Sales Visit by {self.session_id.user_id.name}.\nContact Person: {self.contact_name or ''}\nNotes: {self.notes or ''}",
            })
            # If contact name is given separately from company name, create child contact under company
            if self.contact_name and self.company_name and self.contact_name != self.company_name:
                Partner.create({
                    'name': self.contact_name,
                    'parent_id': new_partner.id,
                    'type': 'contact',
                    'phone': phone,
                    'email': self.email,
                    'user_id': salesperson_id,
                })
            return new_partner

    def _create_lead(self):
        self.ensure_one()
        CrmLead = self.env['crm.lead'].sudo()
        phone = self._get_formatted_phone()
        subject_name = self.contact_name or self.company_name or phone or "Field Visit"
        lead_name = f"Lead from Visit: {subject_name}"

        lead_vals = {
            'name': lead_name,
            'contact_name': self.contact_name,
            'partner_name': self.company_name,
            'phone': phone,
            'email_from': self.email,
            'description': self.notes or f"Created from field sales visit session {self.session_id.name}",
            'user_id': self._get_salesperson_id(),
        }
        if self.partner_id:
            lead_vals['partner_id'] = self.partner_id.id

        return CrmLead.create(lead_vals)
