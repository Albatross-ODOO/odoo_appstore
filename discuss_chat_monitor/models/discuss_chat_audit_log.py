# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class DiscussChatAuditLog(models.Model):
    _name = 'discuss.chat.audit.log'
    _description = 'Discuss Chat Security Audit Log'
    _order = 'access_datetime desc, id desc'

    session_id = fields.Many2one('discuss.chat.session', string="Chat Session", required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string="Admin User", default=lambda self: self.env.user, required=True, index=True)
    access_datetime = fields.Datetime(string="Access Timestamp", default=fields.Datetime.now, required=True, index=True)
    action_type = fields.Selection([
        ('view', 'Viewed Session'),
        ('refresh', 'Refreshed Stream'),
        ('flag', 'Flagged / Unflagged'),
        ('export', 'Exported Transcript')
    ], string="Action Executed", default='view', required=True)
    notes = fields.Text(string="Audit Details / Notes")
