# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime, time
from odoo import api, fields, models, _
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)

# Keywords for compliance auto-flagging (can be expanded)
SENSITIVE_KEYWORDS = ['password', 'secret', 'bank', 'credit card', 'confidential', 'ssn', 'credentials', 'hacked']


class DiscussChatSession(models.Model):
    _name = 'discuss.chat.session'
    _description = 'Daily Discuss Chat Session'
    _order = 'session_date desc, last_message_time desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string="Session Title", compute='_compute_name', store=True, index=True)
    session_date = fields.Date(string="Date", default=fields.Date.context_today, required=True, index=True)
    channel_id = fields.Many2one('discuss.channel', string="Channel", required=True, ondelete='cascade', index=True)
    channel_type = fields.Selection(related='channel_id.channel_type', string="Channel Type", store=True, readonly=True)
    
    participant_ids = fields.Many2many('res.partner', 'chat_session_partner_rel', 'session_id', 'partner_id', string="Participants", index=True)
    user_ids = fields.Many2many('res.users', string="Participant Users", compute='_compute_user_ids', store=True)
    participant_summary = fields.Char(string="Participants Summary", compute='_compute_participant_summary', store=True)
    
    message_ids = fields.Many2many('mail.message', 'chat_session_message_rel', 'session_id', 'message_id', string="Messages")
    message_count = fields.Integer(string="Message Count", compute='_compute_session_details', store=True)
    first_message_time = fields.Datetime(string="First Message", compute='_compute_session_details', store=True)
    last_message_time = fields.Datetime(string="Last Message", compute='_compute_session_details', store=True)
    
    chat_transcript_html = fields.Html(string="Chat Transcript Thread", compute='_compute_session_details', store=True, sanitize=False)
    
    state = fields.Selection([
        ('active', 'Active'),
        ('flagged', 'Flagged'),
        ('archived', 'Closed/Archived')
    ], string="Status", default='active', required=True, index=True)
    
    is_flagged = fields.Boolean(string="Is Flagged", default=False, index=True)
    flag_reason = fields.Char(string="Flag Reason")
    
    audit_log_ids = fields.One2many('discuss.chat.audit.log', 'session_id', string="Audit Logs")
    audit_count = fields.Integer(string="Views Count", compute='_compute_audit_count')

    _sql_constraints = [
        ('channel_date_unique', 'unique(channel_id, session_date)', 'A chat session record already exists for this channel on this date!')
    ]

    @api.depends('channel_id', 'session_date', 'participant_summary')
    def _compute_name(self):
        for record in self:
            date_str = record.session_date.strftime('%Y-%m-%d') if record.session_date else ''
            participants = record.participant_summary or 'Unknown'
            type_label = "Direct Chat" if record.channel_type == 'chat' else "Group Chat"
            record.name = f"[{date_str}] {type_label}: {participants}"

    @api.depends('participant_ids')
    def _compute_user_ids(self):
        for record in self:
            record.user_ids = record.participant_ids.mapped('user_ids')

    @api.depends('participant_ids')
    def _compute_participant_summary(self):
        for record in self:
            names = record.participant_ids.mapped('name')
            record.participant_summary = ", ".join(names) if names else "No participants"

    @api.depends('audit_log_ids')
    def _compute_audit_count(self):
        for record in self:
            record.audit_count = len(record.audit_log_ids)

    @api.depends('channel_id', 'session_date')
    def _compute_session_details(self):
        for record in self:
            if not record.channel_id or not record.session_date:
                record.message_ids = False
                record.message_count = 0
                record.first_message_time = False
                record.last_message_time = False
                record.chat_transcript_html = "<div class='text-muted p-3'>No messages available.</div>"
                continue

            start_dt = datetime.combine(record.session_date, time.min)
            end_dt = datetime.combine(record.session_date, time.max)

            # Query mail.message for this channel on session_date using sudo to bypass standard partner channel restrictions
            messages = self.env['mail.message'].sudo().search([
                ('model', '=', 'discuss.channel'),
                ('res_id', '=', record.channel_id.id),
                ('date', '>=', start_dt),
                ('date', '<=', end_dt),
                ('message_type', 'in', ['comment', 'email', 'notification'])
            ], order='date asc')

            record.message_ids = [(6, 0, messages.ids)]
            record.message_count = len(messages)
            record.first_message_time = messages[0].date if messages else False
            record.last_message_time = messages[-1].date if messages else False

            # Auto-flagging logic for sensitive keywords
            flagged = False
            reasons = []
            for msg in messages:
                body_lower = (msg.body or '').lower()
                for kw in SENSITIVE_KEYWORDS:
                    if kw in body_lower and kw not in reasons:
                        reasons.append(kw)
                        flagged = True

            if flagged and not record.is_flagged:
                record.is_flagged = True
                record.flag_reason = f"Sensitive keyword detected: {', '.join(reasons)}"
                record.state = 'flagged'

            # Build HTML Chat Transcript
            record.chat_transcript_html = record._render_chat_transcript_html(messages)

    def _render_chat_transcript_html(self, messages):
        self.ensure_one()
        if not messages:
            return """
                <div class="cm-chat-empty-container text-center py-5">
                    <i class="fa fa-comments-o fa-3x text-muted mb-3"></i>
                    <h5 class="text-muted fw-normal">No messages posted in this session on this date.</h5>
                </div>
            """

        html = ["""
        <div class="cm-chat-wrapper">
            <div class="cm-chat-header d-flex justify-content-between align-items-center p-3 mb-3 text-white rounded-3 shadow-sm" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);">
                <div class="d-flex align-items-center gap-3">
                    <div class="cm-chat-icon bg-white text-primary rounded-circle d-flex align-items-center justify-content-center fw-bold shadow-sm" style="width: 44px; height: 44px; font-size: 20px;">
                        <i class="fa fa-comments"></i>
                    </div>
                    <div>
                        <h6 class="mb-0 text-white font-weight-bold">""" + html_escape(self.participant_summary or 'Direct Chat') + """</h6>
                        <small class="text-white-50">""" + self.session_date.strftime('%B %d, %Y') + """ • """ + str(len(messages)) + """ messages</small>
                    </div>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="badge rounded-pill bg-white text-dark shadow-sm px-3 py-2">
                        <i class="fa fa-clock-o me-1 text-primary"></i> """ + (self.first_message_time.strftime('%H:%M') if self.first_message_time else '--') + """ - """ + (self.last_message_time.strftime('%H:%M UTC') if self.last_message_time else '--') + """
                    </span>
                </div>
            </div>
            <div class="cm-chat-stream d-flex flex-column gap-3 p-3 bg-light rounded-3 border">
        """]

        # Loop through messages and render chat bubbles
        for msg in messages:
            author = msg.author_id
            author_name = html_escape(author.name if author else msg.email_from or 'System / Bot')
            author_avatar = f"/web/image/res.partner/{author.id}/avatar_128" if author else "/web/static/img/user_menu_avatar.png"
            msg_time = msg.date.strftime('%H:%M:%S') if msg.date else ''
            msg_body = msg.body or '<em class="text-muted">(Empty message)</em>'

            # Attachments summary
            attachments_html = ""
            if msg.attachment_ids:
                attachments_html = '<div class="cm-chat-attachments mt-2 pt-2 border-top d-flex flex-wrap gap-2">'
                for att in msg.attachment_ids:
                    att_url = f"/web/content/{att.id}?download=true"
                    attachments_html += f'''
                        <a href="{att_url}" target="_blank" class="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1 rounded-pill">
                            <i class="fa fa-paperclip"></i> {html_escape(att.name)}
                        </a>
                    '''
                attachments_html += '</div>'

            html.append(f"""
                <div class="cm-chat-message d-flex gap-3 align-items-start p-2 rounded-3 hover-shadow-sm transition-all" id="msg-{msg.id}">
                    <img src="{author_avatar}" class="rounded-circle shadow-sm flex-shrink-0" style="width: 42px; height: 42px; object-fit: cover;" alt="{author_name}"/>
                    <div class="cm-chat-bubble flex-grow-1 bg-white p-3 rounded-3 border shadow-sm" style="max-width: 85%;">
                        <div class="cm-chat-meta d-flex justify-content-between align-items-center mb-1">
                            <strong class="text-dark me-2">{author_name}</strong>
                            <small class="text-muted"><i class="fa fa-clock-o me-1"></i>{msg_time}</small>
                        </div>
                        <div class="cm-chat-content text-break text-dark mb-0">
                            {msg_body}
                        </div>
                        {attachments_html}
                    </div>
                </div>
            """)

        html.append("""
            </div>
        </div>
        """)

        return "".join(html)

    def action_refresh_session(self):
        """Action to refresh real-time message stream for the session."""
        self.ensure_one()
        self.sudo()._compute_session_details()
        
        # Log view in audit log
        self._log_audit_action('refresh', notes="Refreshed chat stream in real time.")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Chat Session Refreshed'),
                'message': _('The chat transcript has been updated with the latest messages.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_flag_toggle(self):
        for record in self:
            if record.is_flagged:
                record.is_flagged = False
                record.state = 'active'
                record.flag_reason = False
            else:
                record.is_flagged = True
                record.state = 'flagged'
                record.flag_reason = "Manually flagged by Admin"
            record._log_audit_action('flag', notes=f"Toggled flag status to {record.state}.")

    def _log_audit_action(self, action_type='view', notes=None):
        """Logs an admin audit action for this chat session."""
        self.ensure_one()
        current_user = self.env.user
        # Avoid repetitive audit logs within 1 minute for same user/action
        recent_log = self.env['discuss.chat.audit.log'].sudo().search([
            ('session_id', '=', self.id),
            ('user_id', '=', current_user.id),
            ('action_type', '=', action_type),
            ('create_date', '>=', fields.Datetime.now() - fields.search_datetime.timedelta(minutes=1) if hasattr(fields, 'search_datetime') else fields.Datetime.now())
        ], limit=1)

        if not recent_log:
            self.env['discuss.chat.audit.log'].sudo().create({
                'session_id': self.id,
                'user_id': current_user.id,
                'access_datetime': fields.Datetime.now(),
                'action_type': action_type,
                'notes': notes or f"Admin viewed chat session {self.name}",
            })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.participant_ids and rec.channel_id:
                rec.participant_ids = [(6, 0, rec.channel_id.channel_partner_ids.ids)]
        return records

    @api.model
    def _cron_sync_daily_chat_sessions(self):
        """Cron job to sync and group all Discuss chats into Daily Chat Sessions."""
        _logger.info("Starting Discuss Chat Monitor Daily Session Synchronization...")
        today = fields.Date.today()
        start_dt = datetime.combine(today, time.min)

        # Find all discuss channels with messages created today
        channels_with_messages = self.env['mail.message'].sudo().read_group(
            domain=[
                ('model', '=', 'discuss.channel'),
                ('date', '>=', start_dt),
                ('message_type', 'in', ['comment', 'email', 'notification'])
            ],
            fields=['res_id'],
            groupby=['res_id']
        )

        created_count = 0
        updated_count = 0

        for group in channels_with_messages:
            channel_id = group.get('res_id')
            if not channel_id:
                continue

            channel = self.env['discuss.channel'].sudo().browse(channel_id)
            if not channel.exists():
                continue

            # Check if session already exists for today
            session = self.sudo().search([
                ('channel_id', '=', channel.id),
                ('session_date', '=', today)
            ], limit=1)

            if not session:
                session = self.sudo().create({
                    'channel_id': channel.id,
                    'session_date': today,
                    'participant_ids': [(6, 0, channel.channel_partner_ids.ids)],
                })
                created_count += 1
            else:
                session._compute_session_details()
                updated_count += 1

        _logger.info(f"Discuss Chat Monitor Cron Finished: Created {created_count} sessions, updated {updated_count} sessions.")
