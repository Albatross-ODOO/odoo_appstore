from odoo import models, fields, api, _
import random
import string
import base64
from odoo.exceptions import ValidationError
import logging
import uuid
import urllib.parse

_logger = logging.getLogger(__name__)

class GateEntry(models.Model):
    _name = 'gate.entry'
    _description = 'Gate Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference', 
        required=True, 
        copy=False, 
        readonly=True, 
        index=True, 
        default=lambda self: _('New')
    )
    
    entry_type = fields.Selection([
        ('visitor', 'Visitor / Guest'),
        ('vehicle', 'Commercial Vehicle'),
        ('material', 'Material Inward/Outward'),
        ('worker', 'Worker')
    ], string='Entry Type', default='visitor', required=True, tracking=True)

    operation_type = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing')
    ], string='Operation Type', required=True, default='incoming', tracking=True)

    # Visitor Details (Main fields)
    visitor_name = fields.Char(string='Visitor Name', tracking=True)
    mobile_number = fields.Char(string='Mobile Number', tracking=True)
    vehicle_number = fields.Char(string='Vehicle Number', tracking=True)
    
    # Backward compatibility / alias fields for driver info
    driver_name = fields.Char(string='Driver Name', compute='_compute_driver_fields', inverse='_inverse_driver_fields', store=True)
    driver_phone = fields.Char(string='Driver Phone', compute='_compute_driver_fields', inverse='_inverse_driver_fields', store=True)

    vendor_id = fields.Many2one('res.partner', string='Vendor/Supplier', tracking=True)
    worker_id = fields.Many2one('gate.worker', string='Worker', tracking=True)

    # Material Logs (Active if entry_type == 'material')
    material_name = fields.Char(string='Material Name/Description')
    material_slip_no = fields.Char(string='Challan / Gate Pass Slip No.')
    material_qty = fields.Float(string='Quantity')
    material_flow = fields.Selection([('inward', 'Inward'), ('outward', 'Outward')], string='Flow')

    # Host/Meeting Info
    host_id = fields.Many2one('res.users', string='Host Name', default=lambda self: self.env.user, tracking=True)
    host_department = fields.Char(string='Host Department', compute='_compute_host_department', store=True, readonly=False)

    # Kiosk Mode fields
    visit_purpose = fields.Selection([
        ('meeting', 'Meeting / Appointment'),
        ('plant_visit', 'Plant Visit'),
        ('maintenance', 'Maintenance / Repair'),
        ('interview', 'Job Interview'),
        ('other', 'Other Purpose')
    ], string='Purpose of Visit', default='meeting', tracking=True)
    visit_purpose_detail = fields.Char(string='Purpose Details', help='Detailed description if purpose is Other')

    # Multi-Company support
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    # OTP Verification
    otp = fields.Char(string='OTP', readonly=True, copy=False, default=lambda self: ''.join(random.choices(string.digits, k=6)))
    otp_verified = fields.Boolean(string='OTP Verified', default=False, tracking=True)
    scan_code = fields.Char(string='Scanned Code', help="Barcode or QR code scanned data")
    qr_code_image = fields.Binary(string="QR Code Image", compute='_compute_qr_code_image', store=True)

    # Photo & Timestamps
    entry_photo = fields.Binary(string='Entry Photo', attachment=True)
    check_in_time = fields.Datetime(string='Check-In Time', readonly=True, tracking=True)
    check_out_time = fields.Datetime(string='Check-Out Time', readonly=True, tracking=True)
    
    # Keeping old fields updated for compatibility
    entry_time = fields.Datetime(string='Entry Time', readonly=True, tracking=True)
    exit_time = fields.Datetime(string='Exit Time', readonly=True, tracking=True)
    exit_remarks = fields.Text(string='Exit Remarks')

    # Scheduling / Invitation Fields
    scheduled_start = fields.Datetime(string='Scheduled From', tracking=True)
    scheduled_end = fields.Datetime(string='Scheduled To', tracking=True)
    invite_message = fields.Text(string='Shareable Invite', compute='_compute_invite_message')
    
    access_token = fields.Char(string='Access Token', default=lambda self: str(uuid.uuid4()), copy=False)
    share_link = fields.Char(string='Share Link', compute='_compute_share_link')
    google_maps_link = fields.Char(string='Google Maps Link', compute='_compute_google_maps_link')
    validity_string = fields.Char(string='Validity Period', compute='_compute_validity_string', store=True)
    full_address = fields.Char(string='Full Address', compute='_compute_full_address', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('otp_sent', 'OTP Sent'),
        ('verified', 'Verified'),
        ('authorized', 'Authorized'),
        ('entered', 'Inside Premises'),
        ('exited', 'Exited'),
        ('cancel', 'Cancelled')
    ], string='Status', required=True, readonly=True, copy=False, tracking=True, default='draft')

    @api.depends('visitor_name', 'mobile_number')
    def _compute_driver_fields(self):
        for record in self:
            record.driver_name = record.visitor_name
            record.driver_phone = record.mobile_number

    def _inverse_driver_fields(self):
        for record in self:
            if record.driver_name:
                record.visitor_name = record.driver_name
            if record.driver_phone:
                record.mobile_number = record.driver_phone

    @api.depends('host_id')
    def _compute_host_department(self):
        for record in self:
            if record.host_id and hasattr(record.host_id, 'employee_id') and record.host_id.employee_id and hasattr(record.host_id.employee_id, 'department_id') and record.host_id.employee_id.department_id:
                record.host_department = record.host_id.employee_id.department_id.name
            else:
                record.host_department = False

    @api.depends('company_id')
    def _compute_google_maps_link(self):
        for record in self:
            company = record.company_id
            addr_parts = [company.street, company.street2, company.city, company.state_id.name, company.country_id.name]
            addr_str = ", ".join([p for p in addr_parts if p])
            if addr_str:
                record.google_maps_link = f"https://www.google.com/maps/dir/?api=1&destination={urllib.parse.quote(addr_str)}"
            else:
                record.google_maps_link = "https://maps.google.com"

    @api.depends('company_id', 'company_id.street', 'company_id.street2', 'company_id.city', 'company_id.state_id', 'company_id.country_id')
    def _compute_full_address(self):
        for record in self:
            company = record.company_id
            if company:
                addr_parts = [company.street, company.street2, company.city, company.state_id.name, company.country_id.name]
                addr_str = ", ".join([p for p in addr_parts if p])
                record.full_address = addr_str or "Office Address"
            else:
                record.full_address = "Office Address"

    @api.depends('scheduled_start', 'scheduled_end')
    def _compute_validity_string(self):
        import pytz
        for record in self:
            if record.scheduled_start and record.scheduled_end:
                user_tz_name = self.env.user.tz or 'Asia/Kolkata'
                try:
                    user_tz = pytz.timezone(user_tz_name)
                except Exception:
                    user_tz = pytz.timezone('Asia/Kolkata')
                
                start_dt = record.scheduled_start
                end_dt = record.scheduled_end
                
                if start_dt.tzinfo is None:
                    start_dt = pytz.utc.localize(start_dt).astimezone(user_tz)
                else:
                    start_dt = start_dt.astimezone(user_tz)
                
                if end_dt.tzinfo is None:
                    end_dt = pytz.utc.localize(end_dt).astimezone(user_tz)
                else:
                    end_dt = end_dt.astimezone(user_tz)
                
                date_str = start_dt.strftime('%d %b %Y')
                start_time = start_dt.strftime('%I:%M %p')
                end_time = end_dt.strftime('%I:%M %p')
                record.validity_string = f"{date_str}, {start_time} - {end_time}"
            else:
                record.validity_string = False

    @api.depends('otp')
    def _compute_qr_code_image(self):
        for record in self:
            if record.otp:
                try:
                    # Use Odoo's native QR code generator (no external dependencies)
                    barcode_content = self.env['ir.actions.report'].sudo().barcode('QR', record.otp, width=300, height=300)
                    if barcode_content:
                        record.qr_code_image = base64.b64encode(barcode_content)
                    else:
                        record.qr_code_image = False
                except Exception as e:
                    _logger.error(f"Failed to generate QR code using native Odoo report: {e}")
                    # Fallback to qrcode library if available
                    try:
                        import qrcode
                        from io import BytesIO
                        qr = qrcode.QRCode(
                            version=1,
                            error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=10,
                            border=4,
                        )
                        qr.add_data(record.otp)
                        qr.make(fit=True)
                        img = qr.make_image(fill_color="black", back_color="white")
                        temp = BytesIO()
                        img.save(temp, format="PNG")
                        record.qr_code_image = base64.b64encode(temp.getvalue())
                    except Exception as e2:
                        _logger.error(f"Fallback QR generation failed: {e2}")
                        record.qr_code_image = False
            else:
                record.qr_code_image = False

    def _compute_share_link(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or 'http://localhost:8069'
        if 'localhost' in base_url or '127.0.0.1' in base_url:
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                base_url = base_url.replace('localhost', local_ip).replace('127.0.0.1', local_ip)
            except Exception:
                pass
        db_name = self.env.cr.dbname
        for record in self:
            token = record.access_token or str(uuid.uuid4())
            if not record.access_token:
                record.access_token = token
            # Appending db parameter to avoid database selector redirects for public users
            record.share_link = f"{base_url}/gate/invitation/share?id={record.id}&token={token}&db={db_name}"

    def action_open_share_wizard(self):
        """ Ensures token exists and opens the share wizard """
        self.ensure_one()
        if not self.access_token:
            self.access_token = str(uuid.uuid4())
        
        return {
            'name': _('Share Invitation'),
            'type': 'ir.actions.act_window',
            'res_model': 'gate.share.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_entry_id': self.id},
        }

    @api.depends('name', 'otp', 'scheduled_start', 'scheduled_end', 'vehicle_number', 'company_id', 'google_maps_link', 'visit_purpose', 'visit_purpose_detail')
    def _compute_invite_message(self):
        for record in self:
            if record.state == 'scheduled' and record.otp:
                msg = f"INVITATION\n"
                msg += f"Ref: {record.name}\n"
                msg += f"Entry Code: {record.otp}\n"
                if record.visit_purpose:
                    purpose = dict(self._fields['visit_purpose'].selection).get(record.visit_purpose)
                    if record.visit_purpose == 'other' and record.visit_purpose_detail:
                        purpose = record.visit_purpose_detail
                    msg += f"Purpose: {purpose}\n"
                if record.scheduled_start and record.scheduled_end:
                   msg += f"Valid: {record.scheduled_start} to {record.scheduled_end}\n"
                if record.vehicle_number:
                   msg += f"Vehicle: {record.vehicle_number}\n"
                msg += f"Google Map: {record.google_maps_link}\n"
                msg += f"Digital Pass: {record.share_link}\n"
                record.invite_message = msg
            else:
                record.invite_message = False

    @api.constrains('vehicle_number', 'state')
    def _check_active_entry(self):
        for record in self:
            if record.state == 'entered' and record.vehicle_number:
                duplicate = self.search([
                    ('id', '!=', record.id),
                    ('vehicle_number', '=', record.vehicle_number),
                    ('state', '=', 'entered')
                ])
                if duplicate:
                    raise ValidationError(_("Vehicle %s is already inside the premises (Ref: %s).") % (record.vehicle_number, duplicate[0].name))

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if vals.get('operation_type') == 'outgoing':
                vals['name'] = self.env['ir.sequence'].next_by_code('gate.entry.out') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('gate.entry.in') or _('New')
        return super(GateEntry, self).create(vals)

    def action_schedule(self):
        """ Schedule the entry and generate OTP """
        for record in self:
            if not record.scheduled_start or not record.scheduled_end:
                 raise ValidationError(_("Please specify both Scheduled From and Scheduled To times."))
            if not record.visitor_name:
                 raise ValidationError(_("Visitor Name is required to schedule an invitation."))
            
            # Generate OTP
            record.otp = ''.join(random.choices(string.digits, k=6))
            record.state = 'scheduled'

    def _send_otp_sms(self):
        """ Extensible helper method for SMS gateway integration """
        self.ensure_one()
        sms_gateway = self.env['ir.config_parameter'].sudo().get_param('gate_management.sms_gateway')
        if sms_gateway:
            _logger.info("Sending OTP via SMS gateway %s to %s", sms_gateway, self.mobile_number)
            self.message_post(body=f"OTP {self.otp} sent to {self.mobile_number} via {sms_gateway}.")
        else:
            self.message_post(body=f"OTP Generated: {self.otp}. (Connect SMS Gateway to send to {self.mobile_number})")

    def action_generate_otp(self):
        """ Generates a 6-digit numeric OTP """
        for record in self:
            record.otp = ''.join(random.choices(string.digits, k=6))
            record.state = 'otp_sent'
            record._send_otp_sms()

    def action_verify_otp(self):
        """ Verifies the OTP """
        for record in self:
            if not record.otp:
               raise ValidationError(_("No OTP generated yet."))
            record.otp_verified = True
            record.state = 'verified'

    def action_print_invitation(self):
        for record in self:
            if not record.otp:
                record.action_schedule()
        return self.env.ref('gate_management.action_report_gate_invitation').report_action(self)

    def action_send_whatsapp_invitation(self):
        self.ensure_one()
        
        # 1. Retrieve the XML template using its XML External ID
        template = self.env.ref('gate_management.wa_template_gate_pass_invitation', raise_if_not_found=False)
        if not template:
            raise ValidationError(_("WhatsApp template for gate pass invitation not found."))
            
        # 2. Grab your generated card image attachment
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('mimetype', 'like', 'image')
        ], limit=1)
        
        if not attachment and self.qr_code_image:
            attachment = self.env['ir.attachment'].create({
                'name': f'QR_{self.name}.png',
                'type': 'binary',
                'datas': self.qr_code_image,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'image/png'
            })
            
        if template:
            if template.status != 'approved':
                # In development/draft state, raise a message to guide the user on template status
                raise ValidationError(_(
                    "The WhatsApp template '%s' is currently in '%s' status. "
                    "It must be 'Approved' by Meta to send invitations."
                ) % (template.name, template.status.upper()))
                
            # 3. Create the composer instance natively
            composer = self.env['whatsapp.composer'].with_context(
                active_model=self._name,
                active_ids=[self.id],
                active_id=self.id,
            ).create({
                'wa_template_id': template.id,
                'res_model': self._name,
                'res_ids': str([self.id]),
                'attachment_id': attachment.id if attachment else False
            })
            
            # 4. Fire message instantly
            composer._send_whatsapp_template()
            self.message_post(body=_("WhatsApp invitation sent successfully using template: %s") % template.name)

    def action_authorize(self):
        self.write({'state': 'authorized'})

    def action_confirm_entry(self):
        for record in self:
            if record.entry_type in ['visitor', 'vehicle'] and not record.entry_photo:
                raise ValidationError(_("Visitor photo is required to confirm entry."))
            record.write({
                'state': 'entered',
                'entry_time': fields.Datetime.now(),
                'check_in_time': fields.Datetime.now()
            })
        
        # Return action to redirect to a brand new blank Walk-In Visitor Entry kiosk form
        return {
            'type': 'ir.actions.act_window',
            'name': _('Walk-In Visitor Entry'),
            'res_model': 'gate.entry',
            'view_mode': 'form',
            'view_id': self.env.ref('gate_management.view_gate_entry_form_kiosk').id,
            'target': 'current',
            'context': {
                'default_entry_type': 'visitor',
                'default_operation_type': 'incoming',
                'default_state': 'draft'
            }
        }

    def action_exit(self):
        for record in self:
            record.write({
                'state': 'exited',
                'exit_time': fields.Datetime.now(),
                'check_out_time': fields.Datetime.now()
            })
            if record.entry_type == 'worker' and record.worker_id:
                # Find the latest inside log for this worker and check out
                latest_log = self.env['gate.worker.log'].search([
                    ('worker_id', '=', record.worker_id.id),
                    ('state', '=', 'inside')
                ], order='check_in_time desc', limit=1)
                if latest_log:
                    latest_log.write({
                        'check_out_time': fields.Datetime.now(),
                        'state': 'outside'
                    })

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_send_email_invitation(self):
        """ Opens a mail composer with predefined email body containing QR/OTP details """
        self.ensure_one()
        body = f"<p>Hello {self.visitor_name or 'Guest'},</p>"
        body += f"<p>You have been invited to visit. Please find your invitation details below:</p>"
        body += f"<ul>"
        body += f"<li><strong>Entry Code (OTP):</strong> {self.otp or ''}</li>"
        if self.scheduled_start and self.scheduled_end:
            body += f"<li><strong>Validity:</strong> {self.scheduled_start} to {self.scheduled_end}</li>"
        if self.vehicle_number:
            body += f"<li><strong>Vehicle Number:</strong> {self.vehicle_number}</li>"
        if self.google_maps_link:
            body += f"<li><strong>Google Map Location:</strong> <a href='{self.google_maps_link}' target='_blank'>Get Directions</a></li>"
        body += f"</ul>"
        body += f"<p>Show the OTP/QR code to the guard at the entrance.</p>"
        body += f"<p>Thank you!</p>"

        composer_context = {
            'default_model': 'gate.entry',
            'default_res_id': self.id,
            'default_use_template': False,
            'default_body': body,
            'default_subject': f"Invitation Pass - {self.name}",
            'default_composition_mode': 'comment',
        }
        return {
            'name': _('Send Email Invitation'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': composer_context,
        }

    @api.model
    def _cron_auto_exit(self):
        """ Automatically marks entries as exited if their scheduled end time has passed. """
        expired_entries = self.search([
            ('state', '=', 'entered'),
            ('scheduled_end', '<', fields.Datetime.now())
        ])
        for entry in expired_entries:
            entry.action_exit()
            entry.message_post(body="Auto-exited by system scheduler.")
