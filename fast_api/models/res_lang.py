# Copyright 2026 Albatross
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from accept_language import parse_accept_language

from odoo import api, models


class ResLang(models.Model):
    _inherit = "res.lang"

    @api.model
    @api.ormcache("accept_language")
    def _get_lang_from_accept_language(self, accept_language):
        """Return the installed language code that best matches an
        ``Accept-Language`` header, or ``None``.

        Languages are tried in the header's order of preference. An exact
        locale (``fr_BE``) wins; otherwise the first installed locale of the
        same language (``fr`` -> ``fr_FR`` or ``fr_BE``) is used.
        """
        if not accept_language:
            return None
        installed = [code for code, _name in self.get_installed()]
        first_by_language = {}
        for code in installed:
            first_by_language.setdefault(code.split("_")[0], code)
        for wanted in parse_accept_language(accept_language):
            if wanted.locale in installed:
                return wanted.locale
            if wanted.language in first_by_language:
                return first_by_language[wanted.language]
        return None
