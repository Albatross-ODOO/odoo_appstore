from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import urllib.parse

class VerifyOtpWizard(models.TransientModel):
    _name = 'gate.verify.otp.wizard'
    _description = 'Verify Visitor OTP'

    state = fields.Selection([
        ('scan', 'Scan OTP'),
        ('photo', 'Take Photo'),
        ('done', 'Done')
    ], default='scan', string='Status')

    otp_code = fields.Char(string='Entry Code / OTP')
    entry_id = fields.Many2one('gate.entry', string='Matched Entry')
    photo = fields.Binary(string='Visitor Photo', attachment=True)
    force_camera_open = fields.Boolean(default=False)

    @api.onchange('otp_code')
    def _onchange_otp_code(self):
        if self.otp_code and len(self.otp_code) >= 6:
            code = self.otp_code.strip()
            
            # Search entry by OTP, reference name, or parsed URL
            entry = self.env['gate.entry'].search([('otp', '=', code)], limit=1)
            if not entry:
                entry = self.env['gate.entry'].search([('name', '=', code)], limit=1)
            if not entry and 'id=' in code:
                try:
                    params = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)
                    entry_id_val = params.get('id', [None])[0]
                    token_val = params.get('token', [None])[0]
                    if entry_id_val:
                        entry = self.env['gate.entry'].search([('id', '=', int(entry_id_val)), ('access_token', '=', token_val)], limit=1)
                except Exception:
                    pass

            if entry:
                if entry.state == 'entered':
                     return {
                        'warning': {
                            'title': _('Already Entered'),
                            'message': _('Visitor %s is already inside.') % (entry.visitor_name or 'Unknown')
                        }
                    }
                
                try:
                    if entry.state in ['scheduled', 'otp_sent']:
                        entry.action_verify_otp()
                    if entry.state in ['draft', 'verified']:
                        entry.action_authorize()
                    
                    self.entry_id = entry.id
                    self.state = 'photo'
                    self.force_camera_open = True
                except Exception as e:
                    return {
                        'warning': {
                            'title': _('Verification Error'),
                            'message': str(e)
                        }
                    }

    def action_verify(self):
        self.ensure_one()
        code = self.otp_code.strip() if self.otp_code else ''
        
        entry = self.env['gate.entry'].search([('otp', '=', code)], limit=1)
        if not entry:
            entry = self.env['gate.entry'].search([('name', '=', code)], limit=1)
        if not entry and 'id=' in code:
            try:
                params = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)
                entry_id_val = params.get('id', [None])[0]
                token_val = params.get('token', [None])[0]
                if entry_id_val:
                    entry = self.env['gate.entry'].search([('id', '=', int(entry_id_val)), ('access_token', '=', token_val)], limit=1)
            except Exception:
                pass

        if not entry:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Invalid Entry Code/Reference: %s') % code,
                    'type': 'danger',
                    'sticky': False,
                }
            }

        if entry.state == 'entered':
             return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Visitor %s is ALREADY ENTERED.') % (entry.visitor_name or 'Unknown'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        try:
            if entry.state in ['scheduled', 'otp_sent']:
                entry.action_verify_otp()
            if entry.state in ['draft', 'verified']:
                entry.action_authorize()
            
            self.write({
                'entry_id': entry.id,
                'state': 'photo',
                'force_camera_open': True
            })

            return {
                'name': _('Verify Entry Code'),
                'type': 'ir.actions.act_window',
                'res_model': 'gate.verify.otp.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Error during verification: %s') % str(e),
                    'type': 'danger',
                    'sticky': False,
                }
            }

    def action_confirm_verification(self):
        self.ensure_one()
        entry = self.entry_id
        
        if not entry:
             raise ValidationError(_("No entry linked to this verification."))

        if self.photo:
            entry.entry_photo = self.photo
            
        try:
            if entry.state in ['scheduled', 'otp_sent']:
                entry.action_verify_otp()
            
            if entry.state == 'verified':
                entry.action_authorize()
                
            if entry.state == 'authorized' or (entry.entry_type == 'material' and entry.state in ['draft', 'verified']):
                if entry.state != 'authorized':
                    entry.write({'state': 'authorized'})
                entry.action_confirm_entry()
                message = _('Success! Entry Confirmed for %s.') % (entry.visitor_name or 'Material/Asset')
                type_msg = 'success'
            else:
                message = _('Could not confirm entry. Current Status: %s') % entry.state
                type_msg = 'warning'

        except Exception as e:
            message = _('Error during verification: %s') % str(e)
            type_msg = 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Result'),
                'message': message,
                'type': type_msg,
                'sticky': False,
                'delay': 5000,
                'next': {
                    'type': 'ir.actions.act_window_close'
                }
            }
        }
