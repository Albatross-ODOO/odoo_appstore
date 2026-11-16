# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class ChatMonitorController(http.Controller):

    @http.route('/discuss_chat_monitor/attachment/<int:attachment_id>', type='http', auth='user', readonly=True)
    def chat_monitor_attachment(self, attachment_id):
        """Download a file shared in a Discuss conversation, for monitors only.

        Monitors get no ORM access to the conversations themselves (that would let them post
        and join), so the file is streamed with sudo after checking the group and that the
        attachment really belongs to a Discuss message."""
        if not request.env.user.has_group('discuss_chat_monitor.group_chat_monitor_admin'):
            raise request.not_found()
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id).exists()
        if not attachment or not request.env['mail.message'].sudo().search_count(
            [('model', '=', 'discuss.channel'), ('attachment_ids', 'in', attachment.ids)], limit=1,
        ):
            raise request.not_found()
        return request.env['ir.binary']._get_stream_from(attachment).get_response(as_attachment=True)
