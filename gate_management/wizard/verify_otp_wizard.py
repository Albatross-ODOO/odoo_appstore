import urllib.parse

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class VerifyOtpWizard(models.TransientModel):
    _name = 'gate.verify.otp.wizard'
    _description = 'Verify Visitor OTP'

    state = fields.Selection([
        ('scan', 'Scan OTP'),
        ('photo', 'Take Photo'),
        ('done', 'Done'),
    ], default='scan', string='Status')

    otp_code = fields.Char(string='Entry Code / OTP')
    entry_id = fields.Many2one('gate.entry', string='Matched Entry')
    photo = fields.Binary(string='Visitor Photo', attachment=True)
    force_camera_open = fields.Boolean(default=False)

    # match card
    visitor_name = fields.Char(related='entry_id.visitor_name')
    entry_name = fields.Char(related='entry_id.name')
    host_name = fields.Char(related='entry_id.host_id.name')
    vehicle_number = fields.Char(related='entry_id.vehicle_number')
    validity_string = fields.Char(related='entry_id.validity_string')
    purpose_label = fields.Char(compute='_compute_match_info')
    window_expired = fields.Boolean(compute='_compute_match_info')
    result_message = fields.Char(string='Result')
    result_time = fields.Char(string='Time')

    def _compute_display_name(self):
        for wiz in self:
            wiz.display_name = _('Verify Invitation')

    @api.depends('entry_id')
    def _compute_match_info(self):
        now = fields.Datetime.now()
        for wiz in self:
            entry = wiz.entry_id
            wiz.purpose_label = entry._purpose_label() if entry else ''
            wiz.window_expired = bool(entry and entry.scheduled_end and entry.scheduled_end < now)

    # ------------------------------------------------------------------
    @api.model
    def _find_entry(self, code):
        code = (code or '').strip()
        if not code:
            return self.env['gate.entry']
        Entry = self.env['gate.entry']
        entry = Entry.search([('otp', '=', code), ('state', 'not in', ('exited', 'cancel'))], limit=1)
        if not entry:
            entry = Entry.search([('name', '=', code)], limit=1)
        if not entry and 'id=' in code:
            try:
                params = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)
                entry_id_val = params.get('id', [None])[0]
                token_val = params.get('token', [None])[0]
                if entry_id_val:
                    entry = Entry.search([('id', '=', int(entry_id_val)), ('access_token', '=', token_val)], limit=1)
            except Exception:
                entry = Entry
        return entry

    def _advance_entry(self, entry):
        if entry.state in ('scheduled', 'otp_sent'):
            entry.action_verify_otp()
        if entry.state in ('draft', 'verified'):
            entry.action_authorize()

    def _reopen(self):
        self.ensure_one()
        return {
            'name': _('Verify Invitation'),
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    @staticmethod
    def _notify(title, message, kind, next_action=None):
        params = {'title': title, 'message': message, 'type': kind, 'sticky': False}
        if next_action:
            params['next'] = next_action
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': params}

    @api.onchange('otp_code')
    def _onchange_otp_code(self):
        if self.otp_code and len(self.otp_code.strip()) >= 6:
            entry = self._find_entry(self.otp_code)
            if entry and entry.state == 'entered':
                return {'warning': {'title': _('Already Entered'), 'message': _('Visitor %s is already inside.') % (entry.visitor_name or _('Unknown'))}}

    def action_verify(self):
        self.ensure_one()
        code = (self.otp_code or '').strip()
        entry = self._find_entry(code)
        if not entry:
            return self._notify(_('Not found'), _('Invalid entry code / reference: %s') % code, 'danger')
        if entry.state == 'entered':
            return self._notify(_('Already inside'), _('%s is already inside the premises.') % (entry.visitor_name or _('This visitor')), 'warning')
        if entry.state in ('exited', 'cancel'):
            return self._notify(_('Pass closed'), _('This pass has already been used or cancelled.'), 'warning')
        try:
            self._advance_entry(entry)
        except Exception as e:
            return self._notify(_('Verification error'), str(e), 'danger')
        self.write({'entry_id': entry.id, 'state': 'photo', 'force_camera_open': True})
        return self._reopen()

    def action_back_to_scan(self):
        self.ensure_one()
        self.write({'state': 'scan', 'otp_code': False, 'entry_id': False, 'photo': False, 'force_camera_open': False})
        return self._reopen()

    def action_confirm_verification(self):
        self.ensure_one()
        entry = self.entry_id
        if not entry:
            raise ValidationError(_("No entry linked to this verification."))
        if self.photo:
            entry.entry_photo = self.photo
        try:
            self._advance_entry(entry)
            if entry.state == 'authorized' or (entry.entry_type == 'material' and entry.state in ('draft', 'verified')):
                if entry.state != 'authorized':
                    entry.write({'state': 'authorized'})
                entry.action_confirm_entry()
                self.write({
                    'state': 'done',
                    'result_message': _('%s is in') % (entry.visitor_name or entry.vehicle_number or _('Material / asset')),
                    'result_time': fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime('%H:%M'),
                })
                return self._reopen()
            return self._notify(_('Not confirmed'), _('Could not confirm entry. Current status: %s') % entry.state, 'warning')
        except Exception as e:
            return self._notify(_('Verification error'), str(e), 'danger')

    def action_next_visitor(self):
        new = self.create({})
        return new._reopen()

    @api.model
    def action_open_kiosk(self):
        return self.create({})._reopen()
