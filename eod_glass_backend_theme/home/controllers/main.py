# -*- coding: utf-8 -*-
"""Home lives at ``/odoo/today``, not ``/odoo/home``.

The web client resolves the first URL segment against its client-action registry before the actions' paths, and
Odoo's own ``home`` client action (web/static/src/webclient/actions/client_actions.js) sends the browser to ``/``.
So a fresh load of ``/odoo/home`` (a reload on Home, a bookmark, a shortcut) ran that action instead of Home: on a
database with Website, ``/`` is the public homepage. Old ``home`` links get a permanent redirect, whatever the
web-client prefix is (a module may serve the backend under another one than ``/odoo``).
"""
from odoo.http import request, route

from odoo.addons.web.controllers import home as web_home

OLD, NEW = "home", "today"


class AicHomeWebClient(web_home.Home):

    @route()
    def web_client(self, s_action=None, **kw):
        parts = request.httprequest.path.split("/")      # ["", "<prefix>", "home", ...]
        if len(parts) > 2 and parts[2] == OLD and parts[1] not in ("web", "scoped_app"):
            parts[2] = NEW
            target = "/".join(parts)
            query = request.httprequest.query_string.decode()
            return request.redirect(target + ("?" + query if query else ""), code=301, local=True)
        return super().web_client(s_action=s_action, **kw)
