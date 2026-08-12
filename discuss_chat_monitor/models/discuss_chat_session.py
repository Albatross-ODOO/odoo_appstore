# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class DiscussChatSession(models.Model):
    _name = 'discuss.chat.session'
    _description = 'Discuss Chat Session'
    _order = 'id desc'

    name = fields.Char(string="Session Title")
    channel_id = fields.Many2one('discuss.channel', string="Channel", required=True, ondelete='cascade')
    channel_type = fields.Selection(related='channel_id.channel_type', string="Channel Type", store=True, readonly=True)
    participant_ids = fields.Many2many('res.partner', string="Participants")
    message_ids = fields.Many2many('mail.message', string="Messages")
    message_count = fields.Integer(string="Message Count")
