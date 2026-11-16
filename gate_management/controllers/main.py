import base64
import logging

from odoo import http
from odoo.http import content_disposition, request
from odoo.tools.misc import consteq

_logger = logging.getLogger(__name__)


class GateInvitation(http.Controller):

    def _get_entry(self, id, token):
        try:
            entry_id = int(id)
        except (TypeError, ValueError):
            return None
        entry = request.env['gate.entry'].sudo().browse(entry_id)
        if not entry.exists() or not entry.access_token or not consteq(entry.access_token.encode(), (token or '').encode()):
            return None
        # the visitor has no Odoo time zone: render the pass in the site's time zone
        request.update_context(tz=entry._pass_tz_name())
        return entry.with_context(tz=entry._pass_tz_name())

    def _render_pass_page(self, entry):
        """The digital pass; a cancelled or used pass only says so (no code, no QR) and answers 410 Gone."""
        closed = entry._pass_closed_reason()
        values = {
            'gate_entry': entry,
            'closed': closed,
            'is_material': entry.entry_type == 'material',
            'download_url': f"{entry._base_url()}/gate/invitation/download?id={entry.id}&token={entry.access_token}&db={request.env.cr.dbname}",
            'qr_base64': '',
        }
        if not closed:
            png = entry._qr_png(entry.otp) if entry.otp else False
            values['qr_base64'] = base64.b64encode(png).decode() if png else ''
        return request.render('gate_management.invitation_landing_page', values, status=410 if closed else 200)

    @http.route('/gate/invitation/share', type='http', auth='public', website=False)
    def share_invitation(self, id=None, token=None, **kwargs):
        entry = self._get_entry(id, token)
        if not entry:
            raise request.not_found()
        return self._render_pass_page(entry)

    @http.route('/gate/invitation/download', type='http', auth='public', website=False)
    def download_invitation(self, id=None, token=None, **kwargs):
        entry = self._get_entry(id, token)
        if not entry:
            raise request.not_found()
        if entry._pass_closed_reason():
            return self._render_pass_page(entry)
        try:
            report_xmlid = entry._pass_report_xmlid()
            pdf_content, _ = request.env['ir.actions.report'].sudo().with_context(tz=entry.env.context.get('tz'))._render_qweb_pdf(report_xmlid, [entry.id])
        except Exception:
            # details go to the server log, not to the anonymous visitor
            _logger.exception("Gate pass PDF could not be generated for %s", entry)
            return request.make_response("The gate pass PDF could not be generated. Please contact the site.",
                                         headers=[('Content-Type', 'text/plain')], status=500)
        return request.make_response(pdf_content, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', content_disposition('%s-%s.pdf' % (entry.entry_type == 'material' and 'GatePass' or 'Invitation', (entry.gate_pass_no or entry.name).replace('/', '-')), disposition_type='inline')),
        ])
