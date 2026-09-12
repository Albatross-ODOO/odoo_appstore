from odoo import http
from odoo.http import request
import base64

class GateInvitation(http.Controller):

    @http.route('/gate/invitation/share', type='http', auth='public')
    def share_invitation(self, id, token, **kwargs):
        try:
            entry_id = int(id)
        except ValueError:
            return request.not_found()

        entry = request.env['gate.entry'].sudo().browse(entry_id)
        
        # Verify token
        if not entry.exists() or not entry.access_token or entry.access_token != token:
            return request.not_found()
        
        # Prepare Download URL
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url') or 'http://localhost:8069'
        if 'localhost' in base_url or '127.0.0.1' in base_url:
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                base_url = base_url.replace('localhost', local_ip).replace('127.0.0.1', local_ip)
            except Exception:
                pass
        db_name = request.env.cr.dbname
        download_url = f"{base_url}/gate/invitation/download?id={entry.id}&token={entry.access_token}&db={db_name}"
        
        # Generate QR Code
        qr_base64 = ""
        qr_error = ""
        try:
            # Attempt 1: Odoo Report Barcode
            barcode_content = request.env['ir.actions.report'].sudo().barcode('QR', entry.otp, width=300, height=300)
            qr_base64 = base64.b64encode(barcode_content).decode()
        except Exception as e:
            qr_error = f"Odoo Barcode Error: {str(e)}"
            # Attempt 2: qrcode library
            try:
                import qrcode
                from io import BytesIO
                img = qrcode.make(entry.otp)
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                qr_base64 = base64.b64encode(buffer.getvalue()).decode()
                qr_error = "" # Clear error if fallback succeeds
            except ImportError:
                qr_error += " | qrcode lib not found."
            except Exception as e2:
                qr_error += f" | Fallback Error: {str(e2)}"

        # Render HTML Landing Page
        return request.render('gate_management.invitation_landing_page', {
            'gate_entry': entry,
            'download_url': download_url,
            'qr_base64': qr_base64,
            'qr_error': qr_error
        })
        
    @http.route('/gate/invitation/download', type='http', auth='public')
    def download_invitation(self, id, token, **kwargs):
        try:
            entry_id = int(id)
        except ValueError:
            return request.not_found()

        entry = request.env['gate.entry'].sudo().browse(entry_id)
        
        # Verify token
        if not entry.exists() or not entry.access_token or entry.access_token != token:
            return request.not_found()
            
        try:
            # Render PDF with explicit sudo on the Report Action
            pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf('gate_management.report_gate_invitation_template', [entry.id])
            
            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_content)),
                ('Content-Disposition', f'inline; filename="Invitation-{entry.name}.pdf"'),
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)
        except Exception as e:
            # Fallback text response if PDF generation fails
            return request.make_response(f"Error creating PDF: {str(e)}", headers=[('Content-Type', 'text/plain')])
