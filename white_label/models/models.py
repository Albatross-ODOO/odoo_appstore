import base64
from odoo import fields, models, tools, exceptions, api

from urllib.parse import urlparse


class ResCompany(models.Model):
    _inherit = "res.company"

    brand_name = fields.Char(
        "Brand name",
        help="Brand Name To Do The Debranding"
    )
    brand_logo = fields.Binary(
        "Brand Logo"
    )
    brand_url = fields.Char("Brand URL")
    favicon = fields.Binary(
        string="Favicon",
        help="This field holds the favicon"
             " used for the Company",
    )
    logo_branding = fields.Binary(
        compute='_compute_logo_branding',
        store=True,
        attachment=False
    )

    @api.depends('brand_logo')
    def _compute_logo_branding(self):
        for company in self:
            img = company.brand_logo
            company.logo_branding = img and base64.b64encode(tools.image_process(base64.b64decode(img), size=(180, 0)))

    @api.model
    def get_current_company_brand_details(self):
        """
        ::data => Brand Name Of Current Logged Company
        """
        company = self.env.company if hasattr(self.env, 'company') else False
        data = {
            "brand_name": (company.brand_name or company.name) if company else "",
            "company_name": company.name if company else ""
        }
        return data


class WebsiteConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    favicon = fields.Binary(
        related='company_id.favicon',
        string="Favicon",
        help="This field holds the favicon"
             " used for the Company",
        readonly=False)
    brand_logo = fields.Binary(
        related='company_id.brand_logo',
        readonly=False
    )
    brand_name = fields.Char(
        related='company_id.brand_name',
        readonly=False
    )
    brand_url = fields.Char(
        related='company_id.brand_url',
        readonly=False
    )

    @api.constrains('brand_url')
    def validate_url(self):
        for record in self:
            if not record.brand_url:
                continue
            try:
                result = urlparse(record.brand_url)
                if not all([result.scheme, result.netloc]):
                    raise exceptions.UserError("URL Validation Failed, URL Must be in a format of http://www.example.com")
            except ValueError:
                raise exceptions.UserError("URL Validation Failed, URL Must be in a format of http://www.example.com")

    # Sample Error Dialogue
    def error(self):
        raise exceptions.ValidationError(
            "This is a test Error message. You dont need to save the config after pop wizard.")

    # Sample Warning Dialogue
    def warning(self):
        raise exceptions.UserError("This is a test Error message. You don't need to save the config after pop wizard.")


class ViewExtend(models.Model):
    _inherit = 'ir.ui.view'

    def _render_template(self, template, values=None):
        if not values:
            values = {}
        if hasattr(self.env, 'company') and self.env.company:
            brand_name = self.env.company.brand_name or self.env.company.name
            if brand_name:
                values["title"] = brand_name
        return super(ViewExtend, self)._render_template(template, values=values)

