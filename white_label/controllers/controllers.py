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
from odoo.addons.web.controllers.database import Database

try:
    from werkzeug.utils import send_file
except ImportError:
    from odoo.tools._vendor.send_file import send_file


class CustomDatabase(Database):
    def _render_template(self, **d):
        res = super(CustomDatabase, self)._render_template(**d)
        if isinstance(res, str):
            res = res.replace('/web/static/img/logo2.png', '/web/binary/company_logo')
            res = res.replace('/web/static/img/logo.png', '/web/binary/company_logo')
            res = res.replace('<title>Odoo</title>', '<title>Database Manager</title>')
        elif isinstance(res, bytes):
            res = res.replace(b'/web/static/img/logo2.png', b'/web/binary/company_logo')
            res = res.replace(b'/web/static/img/logo.png', b'/web/binary/company_logo')
            res = res.replace(b'<title>Odoo</title>', b'<title>Database Manager</title>')
        return res


class CustomHome(Home):

    @http.route('/web/login', type='http', auth='public', website=True, sitemap=False)
    def web_login(self, *args, **kw):
        response = super(CustomHome, self).web_login(*args, **kw)
        # Ensure the response is a rendering of a template
        if response.qcontext:
            company = request.env.company if hasattr(request, 'env') and request.env else None
            brand_name = (company.brand_name or company.name) if company else False
            if brand_name:
                response.qcontext['title'] = brand_name
            if company and company.favicon:
                response.qcontext['favicon'] = f"/web/image/res.company/{company.id}/favicon"
        return response

class ResCompanyLogo(Binary):
    @http.route([
        '/web/binary/company_logo',
        '/logo',
        '/logo.png',
        '/web/static/img/logo.png',
        '/web/static/img/logo2.png',
        '/web/static/img/logo_white.png',
    ], type='http', auth="none", cors="*")
    def company_logo(self, dbname=None, **kw):
        imgname = 'logo'
        imgext = '.png'
        dbname = request.db or (kw.get('dbname') if kw else None)
        if not dbname:
            try:
                dbs = http.db_list()
                if dbs:
                    dbname = dbs[0]
            except Exception:
                dbname = None

        uid = (request.session.uid if dbname and hasattr(request, 'session') else None) or odoo.SUPERUSER_ID


        if not dbname:
            response = http.Stream.from_path(file_path('web/static/img/nologo.png')).get_response()
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
                        if not cr.rowcount:
                            cr.execute("""SELECT logo_branding, write_date FROM res_company ORDER BY id LIMIT 1""")
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
                            if not cr.rowcount:
                                cr.execute("""SELECT logo_web, write_date FROM res_company ORDER BY id LIMIT 1""")
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
                response = http.Stream.from_path(file_path('web/static/img/nologo.png')).get_response()
        return response

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()
        result['brand_name'] = self.env.company.brand_name if self.env.company else ""
        return result

