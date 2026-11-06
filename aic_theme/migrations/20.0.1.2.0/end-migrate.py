# -*- coding: utf-8 -*-
"""20.0.1.2.0 reads SVG logos: companies whose logo is an SVG had no logo colours (Pillow cannot open SVG).

An end- script: it runs once every module is loaded, so the palette is computed with the look's own CSS
(web_theme_eod overrides _aic_palette_css); a post- script of aic_theme would store the engine's generic CSS."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env["res.company"].search([])
    companies._compute_aic_logo_colors()
    companies.flush_recordset()
