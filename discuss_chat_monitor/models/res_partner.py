# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    chat_session_ids = fields.Many2many(
        'discuss.chat.session',
        'chat_session_partner_rel',
        'partner_id',
        'session_id',
        string="Chat Sessions",
        readonly=True
    )
    chat_session_count = fields.Integer(
        string="Total Chat Sessions",
        compute='_compute_chat_stats',
        help="Total number of chat sessions monitored for this partner"
    )
    chatted_partner_ids = fields.Many2many(
        'res.partner',
        string="Chat Connections",
        compute='_compute_chat_stats',
        help="Partners with whom this employee has chatted"
    )
    chatted_partner_count = fields.Integer(
        string="Chat Partners Count",
        compute='_compute_chat_stats'
    )
    last_chat_date = fields.Datetime(
        string="Last Active Chat Time",
        compute='_compute_chat_stats'
    )

    @api.depends('chat_session_ids')
    def _compute_chat_stats(self):
        for partner in self:
            sessions = self.env['discuss.chat.session'].sudo().search([
                ('participant_ids', 'in', partner.id)
            ])
            partner.chat_session_count = len(sessions)
            
            # Find all co-participants in these sessions excluding self
            co_partners = sessions.mapped('participant_ids') - partner
            partner.chatted_partner_ids = [(6, 0, co_partners.ids)]
            partner.chatted_partner_count = len(co_partners)

            # Find last message date
            last_times = sessions.filtered(lambda s: s.last_message_time).mapped('last_message_time')
            partner.last_chat_date = max(last_times) if last_times else False

    def action_open_partner_chat_sessions(self):
        """Action to open all chat sessions for this partner."""
        self.ensure_one()
        return {
            'name': _("Chat Sessions for %s", self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'discuss.chat.session',
            'view_mode': 'kanban,list,form',
            'domain': [('participant_ids', 'in', self.id)],
            'context': {
                'search_default_participant_ids': self.id,
                'default_participant_ids': [(4, self.id)],
            }
        }
