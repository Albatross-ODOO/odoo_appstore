from odoo import models, fields, api
import urllib.parse

class GateShareWizard(models.TransientModel):
    _name = 'gate.share.wizard'
    _description = 'Share Invitation Wizard'

    entry_id = fields.Many2one('gate.entry', required=True)
    share_link = fields.Char(related='entry_id.share_link', readonly=True)
    mobile = fields.Char(related='entry_id.mobile_number', readonly=False, string="WhatsApp Number")
    
    def action_share_whatsapp(self):
        self.ensure_one()
        entry = self.entry_id
        
        # Format Dates in the user's local timezone (Asia/Kolkata fallback)
        import pytz
        user_tz_name = self.env.user.tz or 'Asia/Kolkata'
        try:
            user_tz = pytz.timezone(user_tz_name)
        except Exception:
            user_tz = pytz.timezone('Asia/Kolkata')
            
        start_dt = entry.scheduled_start
        end_dt = entry.scheduled_end
        
        if start_dt:
            if start_dt.tzinfo is None:
                start_dt = pytz.utc.localize(start_dt).astimezone(user_tz)
            else:
                start_dt = start_dt.astimezone(user_tz)
        if end_dt:
            if end_dt.tzinfo is None:
                end_dt = pytz.utc.localize(end_dt).astimezone(user_tz)
            else:
                end_dt = end_dt.astimezone(user_tz)
            
        date_str = start_dt.strftime('%d %b') if start_dt else ""
        start_time = start_dt.strftime('%I:%M %p') if start_dt else ""
        end_time = end_dt.strftime('%I:%M %p') if end_dt else ""
        
        # Host Name (Current User or Creator)
        host_name = self.env.user.name
        
        # Maps Location Link (Dynamic from company address)
        map_link = entry.google_maps_link
        
        # Construct Links (Ensure we provide direct PDF download link as well)
        share_link = self.share_link
        pdf_download_link = f"{share_link.replace('/share', '/download')}"
        
        # Construct Message
        company_name = entry.company_id.name or "our office"
        msg = f"*{host_name}* has invited you to *{company_name}*.\n"
        msg += f"📅 On: {date_str}, from {start_time} to {end_time}\n"
        msg += f"🔑 Entry Code: *{entry.otp}*\n"
        msg += f"📍 Location: {map_link}\n\n"
        msg += f"🎫 View Digital Pass: {share_link}\n"
        msg += f"📄 Download PDF Pass: {pdf_download_link}"
        
        phone = self.mobile or ""
        # Clean phone number
        phone = ''.join(filter(str.isdigit, phone))
        
        url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_send_email(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': {
                'default_model': 'gate.entry',
                'default_res_id': self.entry_id.id,
                'default_body': f"Here is your Gate Pass: {self.share_link}",
                'default_partner_ids': [], 
            },
        }

    def action_download_pdf(self):
        self.ensure_one()
        return self.env.ref('gate_management.action_report_gate_invitation').report_action(self.entry_id)
