import base64
import logging
import random
import re
import string
import urllib.parse
import uuid
from datetime import timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class GateEntry(models.Model):
    _name = 'gate.entry'
    _description = 'Gate Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))

    entry_type = fields.Selection([
        ('visitor', 'Visitor / Guest'),
        ('vehicle', 'Commercial Vehicle'),
        ('material', 'Material Inward/Outward'),
        ('worker', 'Worker'),
    ], string='Entry Type', default='visitor', required=True, tracking=True)

    operation_type = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
    ], string='Operation Type', required=True, default='incoming', tracking=True)

    # Visitor details
    visitor_name = fields.Char(string='Visitor Name', tracking=True)
    mobile_number = fields.Char(string='Mobile Number', tracking=True)
    vehicle_number = fields.Char(string='Vehicle Number', tracking=True)

    # Alias fields kept for compatibility with older data / integrations
    driver_name = fields.Char(string='Driver Name', compute='_compute_driver_fields', inverse='_inverse_driver_fields', store=True)
    driver_phone = fields.Char(string='Driver Phone', compute='_compute_driver_fields', inverse='_inverse_driver_fields', store=True)

    vendor_id = fields.Many2one('res.partner', string='Vendor/Supplier', tracking=True)
    worker_id = fields.Many2one('gate.worker', string='Worker', tracking=True)

    # Material
    material_name = fields.Char(string='Material Name/Description')
    material_slip_no = fields.Char(string='Challan / Gate Pass Slip No.')
    material_qty = fields.Float(string='Quantity')
    material_flow = fields.Selection([('inward', 'Inward'), ('outward', 'Outward')], string='Flow')

    # Host
    host_id = fields.Many2one('res.users', string='Host Name', default=lambda self: self.env.user, tracking=True)
    host_department = fields.Char(string='Host Department', compute='_compute_host_department', store=True, readonly=False)

    visit_purpose = fields.Selection([
        ('meeting', 'Meeting / Appointment'),
        ('plant_visit', 'Plant Visit'),
        ('maintenance', 'Maintenance / Repair'),
        ('interview', 'Job Interview'),
        ('other', 'Other Purpose'),
    ], string='Purpose of Visit', default='meeting', tracking=True)
    visit_purpose_detail = fields.Char(string='Purpose Details', help='Detailed description if purpose is Other')

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    # OTP / QR
    otp = fields.Char(string='OTP', readonly=True, copy=False, default=lambda self: ''.join(random.choices(string.digits, k=6)))
    otp_verified = fields.Boolean(string='OTP Verified', default=False, tracking=True)
    scan_code = fields.Char(string='Scanned Code', help="Barcode or QR code scanned data")
    qr_code_image = fields.Binary(string="QR Code Image", compute='_compute_qr_code_image', store=True)

    # Photo & timestamps
    entry_photo = fields.Binary(string='Entry Photo', attachment=True)
    check_in_time = fields.Datetime(string='Check-In Time', readonly=True, tracking=True)
    check_out_time = fields.Datetime(string='Check-Out Time', readonly=True, tracking=True)
    entry_time = fields.Datetime(string='Entry Time', readonly=True, tracking=True)
    exit_time = fields.Datetime(string='Exit Time', readonly=True, tracking=True)
    exit_remarks = fields.Text(string='Exit Remarks')

    # Scheduling / invitation
    scheduled_start = fields.Datetime(string='Scheduled From', tracking=True)
    scheduled_end = fields.Datetime(string='Scheduled To', tracking=True)
    invite_message = fields.Text(string='Shareable Invite', compute='_compute_invite_message')
    access_token = fields.Char(string='Access Token', default=lambda self: str(uuid.uuid4()), copy=False)
    share_link = fields.Char(string='Share Link', compute='_compute_share_link')
    google_maps_link = fields.Char(string='Google Maps Link', compute='_compute_google_maps_link')
    validity_string = fields.Char(string='Validity Period', compute='_compute_validity_string', store=True)
    full_address = fields.Char(string='Full Address', compute='_compute_full_address', store=True)
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue', search='_search_is_overdue')
    whatsapp_available = fields.Boolean(string='WhatsApp Available', compute='_compute_whatsapp_available')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('otp_sent', 'OTP Sent'),
        ('verified', 'Verified'),
        ('authorized', 'Authorized'),
        ('entered', 'Inside Premises'),
        ('exited', 'Exited'),
        ('cancel', 'Cancelled'),
    ], string='Status', required=True, readonly=True, copy=False, tracking=True, default='draft')

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
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
            employee = getattr(record.host_id, 'employee_id', False) if record.host_id else False
            department = getattr(employee, 'department_id', False) if employee else False
            record.host_department = department.name if department else False

    def _company_address(self):
        company = self.company_id
        parts = [company.street, company.street2, company.city, company.state_id.name, company.country_id.name]
        return ", ".join(p for p in parts if p)

    @api.depends('company_id')
    def _compute_google_maps_link(self):
        for record in self:
            addr = record._company_address()
            record.google_maps_link = (
                f"https://www.google.com/maps/dir/?api=1&destination={urllib.parse.quote(addr)}" if addr else "https://maps.google.com")

    @api.depends('company_id', 'company_id.street', 'company_id.street2', 'company_id.city', 'company_id.state_id', 'company_id.country_id')
    def _compute_full_address(self):
        for record in self:
            record.full_address = record._company_address() or "Office Address"

    def _user_tz(self):
        try:
            return pytz.timezone(self.env.user.tz or 'UTC')
        except Exception:
            return pytz.utc

    def _local(self, dt):
        if not dt:
            return False
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(self._user_tz())

    @api.depends('scheduled_start', 'scheduled_end')
    def _compute_validity_string(self):
        for record in self:
            if record.scheduled_start and record.scheduled_end:
                start, end = record._local(record.scheduled_start), record._local(record.scheduled_end)
                record.validity_string = f"{start.strftime('%d %b %Y')}, {start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"
            else:
                record.validity_string = False

    def _qr_png(self, value):
        """QR as PNG bytes. Odoo's report barcode first, the qrcode library as fallback."""
        try:
            content = self.env['ir.actions.report'].sudo().barcode('QR', value, width=300, height=300)
            if content:
                return content
        except Exception as e:  # pragma: no cover - depends on reportlab
            _logger.warning("Native QR generation failed: %s", e)
        try:
            import qrcode
            from io import BytesIO
            img = qrcode.make(value)
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            _logger.error("Fallback QR generation failed: %s", e)
            return False

    @api.depends('otp')
    def _compute_qr_code_image(self):
        for record in self:
            png = record._qr_png(record.otp) if record.otp else False
            record.qr_code_image = base64.b64encode(png) if png else False

    def _base_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or 'http://localhost:8069'
        if 'localhost' in base_url or '127.0.0.1' in base_url:
            # development convenience: make the share link reachable from a phone on the same network
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                base_url = base_url.replace('localhost', local_ip).replace('127.0.0.1', local_ip)
            except Exception:
                pass
        return base_url

    def _compute_share_link(self):
        base_url = self._base_url()
        db_name = self.env.cr.dbname
        for record in self:
            token = record.access_token or str(uuid.uuid4())
            if not record.access_token:
                record.access_token = token
            record.share_link = f"{base_url}/gate/invitation/share?id={record.id}&token={token}&db={db_name}"

    @api.depends('name', 'otp', 'scheduled_start', 'scheduled_end', 'vehicle_number', 'company_id', 'google_maps_link', 'visit_purpose', 'visit_purpose_detail')
    def _compute_invite_message(self):
        for record in self:
            if record.state == 'scheduled' and record.otp:
                msg = f"INVITATION\nRef: {record.name}\nEntry Code: {record.otp}\n"
                purpose = record._purpose_label()
                if purpose:
                    msg += f"Purpose: {purpose}\n"
                if record.validity_string:
                    msg += f"Valid: {record.validity_string}\n"
                if record.vehicle_number:
                    msg += f"Vehicle: {record.vehicle_number}\n"
                msg += f"Google Map: {record.google_maps_link}\nDigital Pass: {record.share_link}\n"
                record.invite_message = msg
            else:
                record.invite_message = False

    def _purpose_label(self):
        self.ensure_one()
        if not self.visit_purpose:
            return ''
        if self.visit_purpose == 'other' and self.visit_purpose_detail:
            return self.visit_purpose_detail
        return dict(self._fields['visit_purpose'].selection).get(self.visit_purpose, '')

    @api.model
    def _whatsapp_installed(self):
        """True on Enterprise databases where the WhatsApp app is installed."""
        return 'whatsapp.composer' in self.env and 'whatsapp.template' in self.env

    def _compute_whatsapp_available(self):
        available = self._whatsapp_installed()
        for record in self:
            record.whatsapp_available = available

    @api.depends('state', 'scheduled_end')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_overdue = bool(record.state == 'entered' and record.scheduled_end and record.scheduled_end < now)

    def _search_is_overdue(self, operator, value):
        domain = [('state', '=', 'entered'), ('scheduled_end', '<', fields.Datetime.now())]
        if (operator == '=' and value) or (operator == '!=' and not value):
            return domain
        return ['!'] + domain

    # ------------------------------------------------------------------
    # Constraints / onchange / CRUD
    # ------------------------------------------------------------------
    @api.constrains('vehicle_number', 'state')
    def _check_active_entry(self):
        for record in self:
            if record.state == 'entered' and record.vehicle_number:
                duplicate = self.search([
                    ('id', '!=', record.id),
                    ('vehicle_number', '=', record.vehicle_number),
                    ('state', '=', 'entered'),
                ], limit=1)
                if duplicate:
                    raise ValidationError(_("Vehicle %s is already inside the premises (Ref: %s).") % (record.vehicle_number, duplicate.name))

    @api.model
    def _normalize_plate(self, plate):
        if not plate:
            return plate
        return re.sub(r'\s+', ' ', plate.strip()).upper()

    @api.model
    def _normalize_mobile(self, mobile):
        """Keep digits (and a leading +) so numbers match however the guard typed them."""
        if not mobile:
            return mobile
        digits = re.sub(r'[^\d+]', '', mobile.strip())
        return digits if digits else mobile

    @api.onchange('mobile_number')
    def _onchange_mobile_number(self):
        """Repeat visitor: pre-fill the form from the last entry with the same mobile number."""
        digits = ''.join(c for c in (self.mobile_number or '') if c.isdigit())
        if len(digits) < 6 or self.visitor_name or self.entry_type not in ('visitor', 'vehicle'):
            return
        previous = self.search([
            ('mobile_number', 'ilike', digits[-10:]),
            ('visitor_name', '!=', False),
            ('entry_type', 'in', ('visitor', 'vehicle')),
        ], order='create_date desc', limit=1)
        if previous:
            self.visitor_name = previous.visitor_name
            if not self.vehicle_number:
                self.vehicle_number = previous.vehicle_number
            if not self.vendor_id:
                self.vendor_id = previous.vendor_id
            if previous.host_id:
                self.host_id = previous.host_id
            if previous.visit_purpose:
                self.visit_purpose = previous.visit_purpose

    @api.onchange('scheduled_start')
    def _onchange_scheduled_start(self):
        if self.scheduled_start and (not self.scheduled_end or self.scheduled_end <= self.scheduled_start):
            self.scheduled_end = self.scheduled_start + timedelta(hours=2)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                code = 'gate.entry.out' if vals.get('operation_type') == 'outgoing' else 'gate.entry.in'
                vals['name'] = self.env['ir.sequence'].next_by_code(code) or _('New')
            if vals.get('vehicle_number'):
                vals['vehicle_number'] = self._normalize_plate(vals['vehicle_number'])
            if vals.get('mobile_number'):
                vals['mobile_number'] = self._normalize_mobile(vals['mobile_number'])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('vehicle_number'):
            vals['vehicle_number'] = self._normalize_plate(vals['vehicle_number'])
        if vals.get('mobile_number'):
            vals['mobile_number'] = self._normalize_mobile(vals['mobile_number'])
        return super().write(vals)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_schedule(self):
        for record in self:
            if not record.scheduled_start or not record.scheduled_end:
                raise ValidationError(_("Please specify both Scheduled From and Scheduled To times."))
            if record.scheduled_end <= record.scheduled_start:
                raise ValidationError(_("Scheduled To must be after Scheduled From."))
            if not record.visitor_name:
                raise ValidationError(_("Visitor Name is required to schedule an invitation."))
            record.otp = ''.join(random.choices(string.digits, k=6))
            record.state = 'scheduled'

    def _send_otp_sms(self):
        self.ensure_one()
        sms_gateway = self.env['ir.config_parameter'].sudo().get_param('gate_management.sms_gateway')
        if sms_gateway:
            _logger.info("Sending OTP via SMS gateway %s to %s", sms_gateway, self.mobile_number)
            self.message_post(body=_("OTP %s sent to %s via %s.") % (self.otp, self.mobile_number, sms_gateway))
        else:
            self.message_post(body=_("OTP Generated: %s. (Connect SMS Gateway to send to %s)") % (self.otp, self.mobile_number))

    def action_generate_otp(self):
        for record in self:
            record.otp = ''.join(random.choices(string.digits, k=6))
            record.state = 'otp_sent'
            record._send_otp_sms()

    def action_verify_otp(self):
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

    def action_open_share_wizard(self):
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

    def _get_whatsapp_text(self):
        """Plain-text pass, used when the Meta template is not approved yet."""
        self.ensure_one()
        start, end = self._local(self.scheduled_start), self._local(self.scheduled_end)
        host_name = self.host_id.name or self.env.user.name
        company_name = self.company_id.name or "our office"
        share_link = self.share_link
        msg = f"*{host_name}* has invited you to *{company_name}*.\n"
        if start and end:
            msg += f"📅 On: {start.strftime('%d %b')}, from {start.strftime('%I:%M %p')} to {end.strftime('%I:%M %p')}\n"
        msg += f"🔑 Entry Code: *{self.otp}*\n"
        msg += f"📍 Location: {self.google_maps_link}\n\n"
        msg += f"🎫 View Digital Pass: {share_link}\n"
        msg += f"📄 Download PDF Pass: {share_link.replace('/share', '/download')}"
        return msg

    def _get_whatsapp_url(self, phone=None):
        self.ensure_one()
        phone = ''.join(filter(str.isdigit, phone or self.mobile_number or ""))
        return f"https://wa.me/{phone}?text={urllib.parse.quote(self._get_whatsapp_text())}"

    @api.model
    def _get_whatsapp_safe_fields(self):
        return ['name', 'otp', 'validity_string', 'full_address', 'share_link', 'google_maps_link',
                'visitor_name', 'vehicle_number', 'company_id.name', 'host_id.name']

    @api.model
    def _get_or_create_wa_template(self):
        """The Meta template lives in the WhatsApp app (Enterprise). It is created on first use so the
        module itself never depends on `whatsapp` and installs cleanly on Community."""
        if not self._whatsapp_installed():
            return False
        template = self.env.ref('gate_management.wa_template_gate_pass_invitation', raise_if_not_found=False)
        if template:
            return template
        Template = self.env['whatsapp.template'].sudo()
        template = Template.create({
            'name': 'Gate Pass Invitation',
            'template_name': 'gate_pass_invitation',
            'model_id': self.env['ir.model']._get_id('gate.entry'),
            'lang_code': 'en',
            'template_type': 'utility',
            'status': 'draft',
            'header_type': 'text',
            'header_text': 'Gate pass from {{1}}',
            'phone_field': 'mobile_number',
            'body': "You have been invited. Show the entry code or the digital pass to the guard at the gate.\n\n"
                    "*Entry Code:* {{1}}\n*Validity:* {{2}}\n*Location:* {{3}}\n*Digital Pass:* {{4}}",
            'variable_ids': [
                (0, 0, {'name': '{{1}}', 'line_type': 'header', 'field_type': 'field', 'field_name': 'company_id.name', 'demo_value': 'Albatross'}),
                (0, 0, {'name': '{{1}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'otp', 'demo_value': '123456'}),
                (0, 0, {'name': '{{2}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'validity_string', 'demo_value': '13 Jul 2026, 11:30 AM - 05:00 PM'}),
                (0, 0, {'name': '{{3}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'full_address', 'demo_value': '123 Main St, Springfield'}),
                (0, 0, {'name': '{{4}}', 'line_type': 'body', 'field_type': 'field', 'field_name': 'share_link', 'demo_value': 'https://example.com/gate/invitation/share'}),
            ],
        })
        self.env['ir.model.data'].sudo().create({
            'name': 'wa_template_gate_pass_invitation',
            'module': 'gate_management',
            'model': 'whatsapp.template',
            'res_id': template.id,
            'noupdate': True,
        })
        return template

    def action_send_whatsapp_invitation(self):
        """Enterprise only (the button is hidden on Community). Sends the approved Meta template through
        the WhatsApp app; while the template is still pending approval, opens a wa.me link with the pass text
        so the guard can still send it from the gate phone."""
        self.ensure_one()
        if not self._whatsapp_installed():
            raise ValidationError(_("WhatsApp is available on Odoo Enterprise with the WhatsApp app installed."))
        if self.state == 'draft':
            self.action_schedule()
        if not self.mobile_number:
            raise ValidationError(_("Please enter the visitor's mobile number to send the pass on WhatsApp."))
        template = self._get_or_create_wa_template()
        if template and template.status == 'approved':
            composer = self.env['whatsapp.composer'].with_context(
                active_model=self._name, active_ids=[self.id], active_id=self.id,
            ).create({
                'wa_template_id': template.id,
                'res_model': self._name,
                'res_ids': str([self.id]),
            })
            composer._send_whatsapp_template()
            self.message_post(body=_("WhatsApp invitation sent using template: %s") % template.name)
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Sent'), 'message': _('WhatsApp pass sent to %s') % self.mobile_number, 'type': 'success', 'sticky': False},
            }
        self.message_post(body=_(
            "WhatsApp template '%s' is not approved by Meta yet (status: %s); the pass was opened in WhatsApp instead.")
            % (template.name if template else 'Gate Pass Invitation', template.status if template else 'missing'))
        return {'type': 'ir.actions.act_url', 'url': self._get_whatsapp_url(), 'target': 'new'}

    def action_send_email_invitation(self):
        self.ensure_one()
        if self.state == 'draft':
            self.action_schedule()
        body = f"<p>Hello {self.visitor_name or 'Guest'},</p>"
        body += "<p>You have been invited to visit. Please find your invitation details below:</p><ul>"
        body += f"<li><strong>Entry Code (OTP):</strong> {self.otp or ''}</li>"
        if self.validity_string:
            body += f"<li><strong>Validity:</strong> {self.validity_string}</li>"
        if self.vehicle_number:
            body += f"<li><strong>Vehicle Number:</strong> {self.vehicle_number}</li>"
        body += f"<li><strong>Location:</strong> <a href='{self.google_maps_link}' target='_blank'>Get Directions</a></li>"
        body += f"<li><strong>Digital Pass:</strong> <a href='{self.share_link}' target='_blank'>{self.share_link}</a></li>"
        body += "</ul><p>Show the OTP/QR code to the guard at the entrance.</p><p>Thank you!</p>"
        return {
            'name': _('Send Email Invitation'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': 'gate.entry',
                'default_res_ids': [self.id],
                'default_body': body,
                'default_subject': f"Invitation Pass - {self.name}",
                'default_composition_mode': 'comment',
            },
        }

    def action_authorize(self):
        self.write({'state': 'authorized'})

    def action_confirm_entry(self):
        now = fields.Datetime.now()
        for record in self:
            if record.entry_type in ('visitor', 'vehicle') and not record.entry_photo:
                raise ValidationError(_("Visitor photo is required to confirm entry."))
            record.write({'state': 'entered', 'entry_time': now, 'check_in_time': now})
        # kiosk flow: land on a fresh walk-in form for the next visitor
        return self.env['ir.actions.act_window']._for_xml_id('gate_management.action_gate_entry_kiosk_visitor')

    def action_exit(self):
        now = fields.Datetime.now()
        for record in self:
            record.write({'state': 'exited', 'exit_time': now, 'check_out_time': now})
            if record.entry_type == 'worker' and record.worker_id:
                record.worker_id._close_open_shift(now)
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_schedule_another(self):
        return self.env['ir.actions.act_window']._for_xml_id('gate_management.action_gate_entry_schedule')

    def action_open_gate_desk(self):
        return self.env['ir.actions.client']._for_xml_id('gate_management.action_gate_desk_home')

    # ------------------------------------------------------------------
    # Data for the Gate Desk home page (OWL client action)
    # ------------------------------------------------------------------
    def _desk_day_bounds(self):
        tz = self._user_tz()
        local_now = pytz.utc.localize(fields.Datetime.now()).astimezone(tz)
        day_start = tz.localize(local_now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)).astimezone(pytz.utc).replace(tzinfo=None)
        return day_start, day_start + timedelta(days=1)

    def _desk_row(self):
        """One entry as the Gate Desk pages show it."""
        self.ensure_one()
        e = self
        fmt = lambda dt: fields.Datetime.context_timestamp(self, dt).strftime('%H:%M') if dt else ''
        type_labels = dict(self._fields['entry_type'].selection)
        state_labels = dict(self._fields['state'].selection)
        state_labels.update({'entered': _('Inside'), 'exited': _('Exited'), 'otp_sent': _('Code sent')})
        title = e.visitor_name or e.vehicle_number or e.material_name or e.name
        if e.entry_type == 'vehicle' and e.vehicle_number:
            title = e.vehicle_number
        sub = [type_labels.get(e.entry_type, '')]
        if e.entry_type == 'worker' and e.worker_id:
            sub.append(e.worker_id.worker_code or '')
        elif e.entry_type == 'material':
            sub.append(e.material_slip_no or '')
        elif e.vendor_id:
            sub.append(e.vendor_id.name)
        elif e.host_id:
            sub.append(_('Host: %s') % e.host_id.name)
        if e.state == 'entered':
            when = _('in %s') % fmt(e.check_in_time)
        elif e.state == 'exited':
            when = '%s → %s' % (fmt(e.check_in_time), fmt(e.check_out_time)) if e.check_in_time else _('out %s') % fmt(e.check_out_time)
        elif e.scheduled_start:
            when = _('scheduled %s – %s') % (fmt(e.scheduled_start), fmt(e.scheduled_end))
        else:
            when = ''
        return {
            'id': e.id, 'name': e.name, 'type': e.entry_type, 'title': title,
            'subtitle': ' · '.join(x for x in sub if x), 'when': when,
            'time': fmt(e.check_in_time) if e.state == 'entered' else fmt(e.scheduled_start),
            'state': e.state, 'state_label': state_labels.get(e.state, e.state),
            'overdue': e.is_overdue, 'has_photo': bool(e.entry_photo),
        }

    @api.model
    def gate_desk_data(self):
        day_start, day_end = self._desk_day_bounds()
        inside = self.search([('state', '=', 'entered')], order='check_in_time desc', limit=100)
        expected = self.search([('state', 'in', ('scheduled', 'otp_sent', 'verified', 'authorized')), ('scheduled_start', '>=', day_start), ('scheduled_start', '<', day_end)], order='scheduled_start asc', limit=50)
        exited_today = self.search_count([('state', '=', 'exited'), ('check_out_time', '>=', day_start), ('check_out_time', '<', day_end)])
        Worker = self.env['gate.worker']
        workforce = {s: Worker.search_count([('status', '=', 'active'), ('current_state', '=', s)]) for s in ('inside', 'break', 'outside')}
        return {
            'counts': {'inside': len(inside), 'expected': len(expected), 'exited': exited_today},
            'inside': [e._desk_row() for e in inside],
            'expected': [e._desk_row() for e in expected],
            'workforce': workforce,
            'gate': self.env.company.name,
            'guard': self.env.user.name,
            'is_manager': self.env.user.has_group('gate_management.group_gate_manager'),
        }

    @api.model
    def gate_entries_data(self, filter_key='all', term='', limit=200):
        """Rows for the Gate Desk Entries page: today's movements plus everything still open."""
        day_start, day_end = self._desk_day_bounds()
        open_states = ('scheduled', 'otp_sent', 'verified', 'authorized', 'entered')
        domain = [('entry_type', '!=', 'worker'), '|', '|', ('state', 'in', open_states),
                  ('check_out_time', '>=', day_start), ('create_date', '>=', day_start)]
        extra = {
            'inside': [('state', '=', 'entered')],
            'scheduled': [('state', 'in', ('scheduled', 'otp_sent', 'verified', 'authorized'))],
            'exited': [('state', '=', 'exited')],
            'vehicle': [('entry_type', '=', 'vehicle')],
            'material': [('entry_type', '=', 'material')],
        }.get(filter_key, [])
        domain += extra
        term = (term or '').strip()
        if term:
            fields_ = ['name', 'visitor_name', 'vehicle_number', 'mobile_number', 'material_name', 'material_slip_no', 'scan_code']
            search_domain = []
            for i, f in enumerate(fields_):
                search_domain = [(f, 'ilike', term)] if i == 0 else ['|'] + search_domain + [(f, 'ilike', term)]
            domain += search_domain
        entries = self.search(domain, order='check_in_time desc, scheduled_start asc, create_date desc', limit=limit)
        counts = {
            'all': self.search_count(domain[:6]),
            'inside': self.search_count([('entry_type', '!=', 'worker'), ('state', '=', 'entered')]),
            'scheduled': self.search_count([('entry_type', '!=', 'worker'), ('state', 'in', ('scheduled', 'otp_sent', 'verified', 'authorized'))]),
            'exited': self.search_count([('entry_type', '!=', 'worker'), ('state', '=', 'exited'), ('check_out_time', '>=', day_start)]),
        }
        return {'rows': [e._desk_row() for e in entries], 'counts': counts, 'gate': self.env.company.name}

    @api.model
    def _cron_auto_exit(self):
        expired = self.search([('state', '=', 'entered'), ('scheduled_end', '<', fields.Datetime.now())])
        for entry in expired:
            entry.action_exit()
            entry.message_post(body=_("Auto-exited by system scheduler."))
