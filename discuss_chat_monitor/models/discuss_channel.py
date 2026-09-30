# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime, time, timedelta

import babel.dates
import pytz
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import AccessError
from odoo.tools import SQL
from odoo.tools.mail import html_to_inner_content, is_html_empty
from odoo.tools.misc import babel_locale_parse, get_lang, posix_to_ldml

_logger = logging.getLogger(__name__)

MONITOR_GROUP = 'discuss_chat_monitor.group_chat_monitor_admin'


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def _check_chat_monitor_access(self):
        """Both RPCs below read every conversation with sudo(): only monitors may call them."""
        if not self.env.user.has_group(MONITOR_GROUP):
            raise AccessError(_("Only members of the “Chat Monitor Manager” group can use the Chat Monitor."))

    def _get_chat_monitor_formats(self):
        """Babel locale and LDML date / time patterns of the user's language (Settings > Languages)."""
        lang = get_lang(self.env)
        locale = babel_locale_parse(lang.code)
        time_format = lang.short_time_format  # the language's time format without seconds
        return locale, posix_to_ldml(lang.date_format, locale=locale), posix_to_ldml(time_format, locale=locale)

    def _format_local_datetime(self, dt, formats=None):
        """Format a UTC datetime in the user's timezone and language formats, like Discuss:
        'Today at 03:11 PM', 'Yesterday at 17:00' or the full date and time ('08/11/2026 05:00 PM')."""
        if not dt:
            return ''
        locale, date_format, time_format = formats or self._get_chat_monitor_formats()
        local_dt = fields.Datetime.context_timestamp(self, dt)
        user_today = fields.Date.context_today(self)
        msg_date = local_dt.date()
        time_str = babel.dates.format_time(local_dt.time(), format=time_format, locale=locale)

        if msg_date == user_today:
            return _("Today at %(time)s", time=time_str)
        elif msg_date == user_today - timedelta(days=1):
            return _("Yesterday at %(time)s", time=time_str)
        date_str = babel.dates.format_date(msg_date, format=date_format, locale=locale)
        return _("%(date)s %(time)s", date=date_str, time=time_str)

    def _get_chat_monitor_tz(self):
        """Timezone of the context / user, like fields.Date.context_today (UTC when unset or invalid)."""
        tz_name = self.env.context.get('tz') or self.env.user.tz
        try:
            return pytz.timezone(tz_name) if tz_name else pytz.utc
        except pytz.UnknownTimeZoneError:
            return pytz.utc

    def _get_target_date_range(self, date_filter):
        """Return the [start, end) UTC bounds of the local-day window, or None for 'all'."""
        user_today = fields.Date.context_today(self)
        if date_filter == 'today':
            first = last = user_today
        elif date_filter == 'yesterday':
            first = last = user_today - timedelta(days=1)
        elif date_filter == 'this_week':
            first, last = user_today - timedelta(days=6), user_today  # 7 calendar days incl. today
        else:
            return None
        tz = self._get_chat_monitor_tz()

        def to_utc(day):
            return tz.localize(datetime.combine(day, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        return to_utc(first), to_utc(last + timedelta(days=1))

    def _get_chat_monitor_message_domain(self, date_filter):
        domain = [('model', '=', 'discuss.channel')]
        date_range = self._get_target_date_range(date_filter)
        if date_range:
            domain += [('date', '>=', date_range[0]), ('date', '<', date_range[1])]
        return domain, date_range

    def _get_chat_monitor_title(self, partners):
        self.ensure_one()
        partner_names = [p.name for p in partners if p.name]
        if self.channel_type == 'chat':
            return ", ".join(partner_names) if partner_names else _("Direct Chat")
        if self.name:
            # a thread is shown under its parent channel, like in Discuss
            if self.parent_channel_id.name:
                return f"{self.parent_channel_id.name} › {self.name}"
            return self.name
        return ", ".join(partner_names) if partner_names else _("Group Discussion")

    def _get_chat_monitor_participants(self, limit=None):
        """Partners and guests (Live Chat visitors, invitation-link visitors) of the conversation."""
        self.ensure_one()
        members = self.channel_member_ids
        participants = [{
            'id': p.id,
            'name': p.name,
            'avatar': f"/web/image/res.partner/{p.id}/avatar_128",
        } for p in members.partner_id]
        participants += [{
            'id': f"guest_{g.id}",
            'name': g.name,
            'avatar': f"/web/image/mail.guest/{g.id}/avatar_128",
        } for g in members.guest_id]
        return participants[:limit] if limit else participants

    def _get_chat_monitor_type_label(self):
        self.ensure_one()
        labels = {'chat': _("Direct"), 'group': _("Group"), 'channel': _("Channel")}
        if self.channel_type in labels:
            return labels[self.channel_type]
        return dict(self._fields['channel_type']._description_selection(self.env)).get(self.channel_type, self.channel_type)

    @api.model
    def get_monitor_channels(self, search_term=None, filter_type='all', date_filter='all'):
        """RPC method for Chat Monitor client action: Returns list of Discuss sessions/channels matching filters."""
        self._check_chat_monitor_access()
        Message = self.env['mail.message'].sudo()
        # archived partners (e.g. OdooBot, former employees) must still count as participants
        Channel = self.sudo().with_context(active_test=False)

        # archived channels are listed too (marked "Archived"): hiding a channel must not hide its history
        domain = []
        if filter_type in ('chat', 'group'):
            domain.append(('channel_type', '=', filter_type))
        elif filter_type == 'channel':
            # "Channels" also covers the types other apps add (Live Chat, WhatsApp, ...), each shown with its own badge
            domain.append(('channel_type', 'not in', ('chat', 'group')))

        # one grouped query instead of loading every message in Python
        msg_domain, date_range = self._get_chat_monitor_message_domain(date_filter)
        stats = {
            res_id: (count, last_date)
            for res_id, count, last_date in Message._read_group(msg_domain, ['res_id'], ['__count', 'date:max'])
        }
        if date_range:
            domain.append(('id', 'in', list(stats)))
        if search_term:
            domain += [
                '|', '&', ('channel_type', '!=', 'chat'), ('name', 'ilike', search_term),
                '|', ('channel_member_ids.partner_id.name', 'ilike', search_term),
                ('channel_member_ids.guest_id.name', 'ilike', search_term),
            ]
        channels = Channel.search(domain)
        # latest message (by date, like the transcript) of each listed channel, in one query
        last_by_channel = {}
        if res_ids := [c.id for c in channels if c.id in stats]:
            self.env.cr.execute(SQL(
                """SELECT DISTINCT ON (res_id) res_id, id FROM mail_message
                    WHERE model = 'discuss.channel' AND res_id = ANY(%s) %s
                 ORDER BY res_id, date DESC, id DESC""",
                res_ids,
                SQL("AND date >= %s AND date < %s", *date_range) if date_range else SQL(""),
            ))
            last_by_channel = dict(self.env.cr.fetchall())
        Message.browse(list(last_by_channel.values())).fetch(['body', 'date', 'attachment_ids'])
        # newest activity first: date of the last message, then channel creation for empty ones
        channels = channels.sorted(
            key=lambda c: (stats[c.id][1] if c.id in stats else c.create_date, c.id), reverse=True)

        result = []
        formats = self._get_chat_monitor_formats()
        for ch in channels:
            members = ch.channel_member_ids
            count = stats.get(ch.id, (0, False))[0]
            last_msg = Message.browse(last_by_channel.get(ch.id))
            last_msg_time = self._format_local_datetime(last_msg.date, formats) if last_msg else ''
            result.append({
                'id': ch.id,
                'name': ch._get_chat_monitor_title([*members.partner_id, *members.guest_id]),
                'channel_type': ch.channel_type,
                'channel_type_label': ch._get_chat_monitor_type_label(),
                'archived': not ch.active,
                'partners': ch._get_chat_monitor_participants(limit=5),
                'partner_count': len(members.partner_id) + len(members.guest_id),
                'message_count': count,
                'last_message_time': last_msg_time,
                'last_message_preview': self._get_chat_monitor_preview(last_msg),
            })
        return result

    def _get_chat_monitor_preview(self, message):
        if not message:
            return ''
        text = html_to_inner_content(message.body)
        if not text and message.attachment_ids:
            text = "📎 " + ", ".join(message.attachment_ids.mapped('name'))
        if not text:
            text = _("This message has been removed")
        return text[:60] + ('...' if len(text) > 60 else '')

    @api.model
    def get_channel_messages(self, channel_id, date_filter='all', limit=None):
        """RPC method for Chat Monitor client action: Returns full message transcript of channel filtered by date."""
        self._check_chat_monitor_access()
        channel = self.sudo().with_context(active_test=False).browse(int(channel_id))
        if not channel.exists():
            return {'channel': None, 'messages': []}

        members = channel.channel_member_ids
        title = channel._get_chat_monitor_title([*members.partner_id, *members.guest_id])
        partner_list = channel._get_chat_monitor_participants()

        msg_domain, _date_range = self._get_chat_monitor_message_domain(date_filter)
        Message = self.env['mail.message'].sudo()
        msg_domain += [('res_id', '=', channel.id)]
        total = Message.search_count(msg_domain)
        # newest `limit` messages, displayed oldest first
        messages = Message.search(msg_domain, order='date desc, id desc', limit=limit)[::-1]

        message_list = []
        formats = self._get_chat_monitor_formats()
        for msg in messages:
            author = msg.author_id
            guest = msg.author_guest_id
            author_name = author.name if author else (guest.name or msg.email_from or _("System"))
            if author:
                author_avatar = f"/web/image/res.partner/{author.id}/avatar_128"
            elif guest:
                author_avatar = f"/web/image/mail.guest/{guest.id}/avatar_128"
            else:
                author_avatar = "/web/static/img/user_menu_avatar.png"
            date_str = self._format_local_datetime(msg.date, formats)

            attachments = []
            for att in msg.attachment_ids:
                attachments.append({
                    'id': att.id,
                    'name': att.name,
                    'url': f"/discuss_chat_monitor/attachment/{att.id}",
                    'mimetype': att.mimetype,
                })
            body = msg.body or ''
            if is_html_empty(body) and not attachments:
                body = Markup('<p class="text-muted fst-italic mb-0">%s</p>') % _("This message has been removed")

            message_list.append({
                'id': msg.id,
                'author_name': author_name,
                'author_avatar': author_avatar,
                'date': date_str,
                'body': body,
                'attachments': attachments,
            })

        return {
            'channel': {
                'id': channel.id,
                'name': title,
                'channel_type': channel.channel_type,
                'archived': not channel.active,
                'partners': partner_list,
                'message_count': total,
            },
            'messages': message_list
        }
