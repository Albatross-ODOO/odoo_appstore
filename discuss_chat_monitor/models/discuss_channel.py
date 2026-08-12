# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
from datetime import datetime, timedelta
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def _format_local_datetime(self, dt):
        """Format Datetime to local timezone string like Discuss ('Today at 03:11 PM', 'Yesterday at 05:00 PM', 'Aug 11, 2026 05:00 PM')."""
        if not dt:
            return ''
        local_dt = fields.Datetime.context_timestamp(self, dt)
        user_today = fields.Date.context_today(self)
        msg_date = local_dt.date()
        time_str = local_dt.strftime('%I:%M %p')

        if msg_date == user_today:
            return f"Today at {time_str}"
        elif msg_date == user_today - timedelta(days=1):
            return f"Yesterday at {time_str}"
        else:
            return local_dt.strftime('%b %d, %Y %I:%M %p')

    def _get_target_dates(self, date_filter):
        """Return a set of local Date objects matching the date_filter."""
        user_today = fields.Date.context_today(self)
        if date_filter == 'today':
            return {user_today}
        elif date_filter == 'yesterday':
            return {user_today - timedelta(days=1)}
        elif date_filter == 'this_week':
            return {user_today - timedelta(days=i) for i in range(8)}
        return None

    @api.model
    def get_monitor_channels(self, search_term=None, filter_type='all', date_filter='all'):
        """RPC method for Chat Monitor client action: Returns list of Discuss sessions/channels matching filters."""
        domain = []

        # 1. Channel type filter
        if filter_type == 'chat':
            domain.append(('channel_type', '=', 'chat'))
        elif filter_type == 'group':
            domain.append(('channel_type', '=', 'group'))
        elif filter_type == 'channel':
            domain.append(('channel_type', '=', 'channel'))

        target_dates = self._get_target_dates(date_filter)

        # Find matching channel IDs based on messages in date range
        if target_dates is not None:
            all_messages = self.env['mail.message'].sudo().search([
                ('model', '=', 'discuss.channel')
            ], order='date desc')

            matching_channel_ids = set()
            for msg in all_messages:
                if msg.res_id and msg.date:
                    local_date = fields.Datetime.context_timestamp(self, msg.date).date()
                    if local_date in target_dates:
                        matching_channel_ids.add(msg.res_id)

            domain.append(('id', 'in', list(matching_channel_ids)))

        channels = self.sudo().search(domain, order='write_date desc')

        result = []
        for ch in channels:
            partners = ch.channel_partner_ids
            partner_names = [p.name for p in partners if p.name]

            if ch.channel_type == 'chat':
                title = ", ".join(partner_names) if partner_names else _("Direct Chat")
            elif ch.name:
                title = ch.name
            else:
                title = ", ".join(partner_names) if partner_names else _("Group Discussion")

            # Apply search filter
            if search_term:
                st = search_term.lower()
                if st not in title.lower() and not any(st in p.lower() for p in partner_names):
                    continue

            # Fetch messages for this channel
            ch_messages = self.env['mail.message'].sudo().search([
                ('model', '=', 'discuss.channel'),
                ('res_id', '=', ch.id),
            ], order='date desc')

            # Filter messages to target dates if date filter applied
            if target_dates is not None:
                ch_messages = ch_messages.filtered(
                    lambda m: m.date and fields.Datetime.context_timestamp(self, m.date).date() in target_dates
                )

            if not ch_messages and target_dates is not None:
                continue

            last_msg = ch_messages[0] if ch_messages else False
            message_count = len(ch_messages)

            partner_list = []
            for p in partners[:5]:
                partner_list.append({
                    'id': p.id,
                    'name': p.name,
                    'avatar': f"/web/image/res.partner/{p.id}/avatar_128"
                })

            last_msg_time = ''
            last_msg_body = ''
            if last_msg and last_msg.date:
                last_msg_time = self._format_local_datetime(last_msg.date)
                clean_text = re.sub('<[^<]+?>', '', last_msg.body or '').strip()
                last_msg_body = clean_text[:60] + ('...' if len(clean_text) > 60 else '')

            result.append({
                'id': ch.id,
                'name': title,
                'channel_type': ch.channel_type,
                'channel_type_label': 'Direct' if ch.channel_type == 'chat' else ('Group' if ch.channel_type == 'group' else 'Channel'),
                'partners': partner_list,
                'partner_count': len(partners),
                'message_count': message_count,
                'last_message_time': last_msg_time,
                'last_message_preview': last_msg_body,
            })

        return result

    @api.model
    def get_channel_messages(self, channel_id, date_filter='all'):
        """RPC method for Chat Monitor client action: Returns full message transcript of channel filtered by date."""
        channel = self.sudo().browse(int(channel_id))
        if not channel.exists():
            return {'channel': None, 'messages': []}

        partners = channel.channel_partner_ids
        partner_names = [p.name for p in partners if p.name]
        if channel.channel_type == 'chat':
            title = ", ".join(partner_names) if partner_names else _("Direct Chat")
        elif channel.name:
            title = channel.name
        else:
            title = ", ".join(partner_names) if partner_names else _("Group Discussion")

        partner_list = [{
            'id': p.id,
            'name': p.name,
            'avatar': f"/web/image/res.partner/{p.id}/avatar_128"
        } for p in partners]

        messages = self.env['mail.message'].sudo().search([
            ('model', '=', 'discuss.channel'),
            ('res_id', '=', channel.id),
        ], order='date asc')

        target_dates = self._get_target_dates(date_filter)
        if target_dates is not None:
            messages = messages.filtered(
                lambda m: m.date and fields.Datetime.context_timestamp(self, m.date).date() in target_dates
            )

        message_list = []
        for msg in messages:
            author = msg.author_id
            author_name = author.name if author else (msg.email_from or _("System"))
            author_avatar = f"/web/image/res.partner/{author.id}/avatar_128" if author else "/web/static/img/user_menu_avatar.png"
            date_str = self._format_local_datetime(msg.date)

            attachments = []
            for att in msg.attachment_ids:
                attachments.append({
                    'id': att.id,
                    'name': att.name,
                    'url': f"/web/content/{att.id}?download=true",
                    'mimetype': att.mimetype,
                })

            message_list.append({
                'id': msg.id,
                'author_name': author_name,
                'author_avatar': author_avatar,
                'date': date_str,
                'body': msg.body or '',
                'attachments': attachments,
            })

        return {
            'channel': {
                'id': channel.id,
                'name': title,
                'channel_type': channel.channel_type,
                'partners': partner_list,
                'message_count': len(message_list),
            },
            'messages': message_list
        }
