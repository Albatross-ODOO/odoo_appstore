import base64

from odoo import http
from odoo.http import request


class GateInvitation(http.Controller):

    def _get_entry(self, id, token):
        try:
            entry_id = int(id)
        except (TypeError, ValueError):
            return None
        entry = request.env['gate.entry'].sudo().browse(entry_id)
        if not entry.exists() or not entry.access_token or entry.access_token != token:
            return None
        return entry

    @http.route('/gate/invitation/share', type='http', auth='public', website=False)
    def share_invitation(self, id=None, token=None, **kwargs):
        entry = self._get_entry(id, token)
        if not entry:
            return request.not_found()
        download_url = f"{entry._base_url()}/gate/invitation/download?id={entry.id}&token={entry.access_token}&db={request.env.cr.dbname}"
        png = entry._qr_png(entry.otp) if entry.otp else False
        return request.render('gate_management.invitation_landing_page', {
            'gate_entry': entry,
            'download_url': download_url,
            'qr_base64': base64.b64encode(png).decode() if png else '',
        })

    @http.route('/gate/invitation/download', type='http', auth='public', website=False)
    def download_invitation(self, id=None, token=None, **kwargs):
        entry = self._get_entry(id, token)
        if not entry:
            return request.not_found()
        try:
            pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('gate_management.report_gate_invitation_template', [entry.id])
        except Exception as e:
            return request.make_response(f"Error creating PDF: {e}", headers=[('Content-Type', 'text/plain')])
        return request.make_response(pdf_content, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', f'inline; filename="Invitation-{entry.name}.pdf"'),
        ])
