import functools
import io
import odoo
import base64
from odoo import http, models
from odoo.addons.web.controllers.binary import Binary
from odoo.tools import file_path
from odoo.tools.mimetypes import guess_mimetype
from odoo.http import request
from odoo.addons.web.controllers.home import Home

try:
    from werkzeug.utils import send_file
except ImportError:
    from odoo.tools._vendor.send_file import send_file


class CustomHome(Home):

    @http.route('/web/login', type='http', auth='public', website=True, sitemap=False)
    def web_login(self, *args, **kw):
        response = super(CustomHome, self).web_login(*args, **kw)
        # Ensure the response is a rendering of a template
        if response.qcontext:
            response.qcontext.update({
                'title': 'thikedar',  # Overriding the title key
                'favicon': '/custom_module/static/src/img/favicon.ico',  # Adding the favicon key
            })
        return response

class ResCompanyLogo(Binary):
    @http.route([
        '/web/binary/company_logo',
        '/logo',
        '/logo.png',
    ], type='http', auth="none", cors="*")
    def company_logo(self, dbname=None, **kw):
        imgname = 'logo'
        imgext = '.png'
        dbname = request.db
        uid = (request.session.uid if dbname else None) or odoo.SUPERUSER_ID

        if not dbname:
            response = http.Stream.from_path(file_path('web/static/img/logo.png')).get_response()
        else:
            try:
                # create an empty registry
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    company = int(kw['company']) if kw and kw.get('company') else False
                    if company:
                        cr.execute("""SELECT logo_branding, write_date
                        FROM res_company
                        WHERE id = %s""", (company,))
                    else:
                        cr.execute("""SELECT c.logo_branding, c.write_date
                                                FROM res_users u
                                           LEFT JOIN res_company c
                                                  ON c.id = u.company_id
                                               WHERE u.id = %s
                                           """, (uid,))
                    branding = cr.fetchone()
                    if branding and branding[0]:
                        image_base64 = base64.b64decode(branding[0])
                        image_data = io.BytesIO(image_base64)
                        mimetype = guess_mimetype(image_base64, default='image/png')
                        imgext = '.' + mimetype.split('/')[1]
                        if imgext == '.svg+xml':
                            imgext = '.svg'
                        response = send_file(image_data, request.httprequest.environ,
                                             download_name=imgname + imgext, mimetype=mimetype,
                                             last_modified=branding[1])
                    else:
                        if company:
                            cr.execute("""SELECT logo_web, write_date
                                                FROM res_company
                                               WHERE id = %s
                                           """, (company,))
                        else:
                            cr.execute("""SELECT c.logo_web, c.write_date
                                                FROM res_users u
                                           LEFT JOIN res_company c
                                                  ON c.id = u.company_id
                                               WHERE u.id = %s
                                           """, (uid,))
                        row = cr.fetchone()
                        if row and row[0]:
                            image_base64 = base64.b64decode(row[0])
                            image_data = io.BytesIO(image_base64)
                            mimetype = guess_mimetype(image_base64, default='image/png')
                            imgext = '.' + mimetype.split('/')[1]
                            if imgext == '.svg+xml':
                                imgext = '.svg'
                            response = send_file(image_data, request.httprequest.environ,
                                                 download_name=imgname + imgext, mimetype=mimetype,
                                                 last_modified=row[1])
                        else:
                            response = http.Stream.from_path(file_path('web/static/img/nologo.png')).get_response()
            except Exception:
                response = http.Stream.from_path(file_path('web/static/img/logo.png')).get_response()
        return response

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()
        result['brand_name'] = self.env.company.brand_name if self.env.company else ""
        return result
