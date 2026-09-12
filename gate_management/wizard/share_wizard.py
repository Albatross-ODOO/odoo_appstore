from odoo import fields, models


class GateShareWizard(models.TransientModel):
    _name = 'gate.share.wizard'
    _description = 'Share Invitation Wizard'

    entry_id = fields.Many2one('gate.entry', required=True)
    share_link = fields.Char(related='entry_id.share_link', readonly=True)
    mobile = fields.Char(related='entry_id.mobile_number', readonly=False, string="WhatsApp Number")
    whatsapp_available = fields.Boolean(related='entry_id.whatsapp_available')

    def action_share_whatsapp(self):
        self.ensure_one()
        if self.mobile and self.mobile != self.entry_id.mobile_number:
            self.entry_id.mobile_number = self.mobile
        return self.entry_id.action_send_whatsapp_invitation()

    def action_send_email(self):
        self.ensure_one()
        return self.entry_id.action_send_email_invitation()

    def action_download_pdf(self):
        self.ensure_one()
        return self.env.ref('gate_management.action_report_gate_invitation').report_action(self.entry_id)
