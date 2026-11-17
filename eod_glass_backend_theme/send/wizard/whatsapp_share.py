# -*- coding: utf-8 -*-
import re
from urllib.parse import quote

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount, format_date


class AicWhatsappShare(models.TransientModel):
    _name = "aic.whatsapp.share"
    _description = "Share a record on WhatsApp"

    res_model = fields.Char(required=True, readonly=True)
    res_id = fields.Integer(required=True, readonly=True)
    record_name = fields.Char(string="Record", readonly=True)
    partner_id = fields.Many2one("res.partner", string="To")
    phone = fields.Char(string="WhatsApp number", help="Use the international form, for example +91 98250 12345.")
    message = fields.Text(required=True)
    link = fields.Char(string="Document link", readonly=True,
                       help="A secure link the customer can open without logging in.")

    # ------------------------------------------------------------------ defaults
    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        model = self.env.context.get("default_res_model") or values.get("res_model")
        res_id = self.env.context.get("default_res_id") or values.get("res_id")
        if not model or not res_id or model not in self.env:
            return values
        record = self.env[model].browse(res_id).exists()
        if not record:
            return values
        record.check_access("read")
        partner = self._partner_of(record)
        link = self._share_link(record)
        values.update({
            "record_name": record.display_name,
            "partner_id": partner.id if partner else False,
            "phone": self._phone_of(record, partner),
            "link": link,
            "message": self._message_for(record, partner, link),
        })
        return values

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id and self.partner_id.phone:
            self.phone = self._international(self.partner_id.phone, self.partner_id)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _partner_of(record):
        if record._name == "res.partner":
            return record
        if "partner_id" in record._fields and record.partner_id:
            return record.partner_id
        return False

    def _phone_of(self, record, partner):
        phone = ""
        if record._name == "crm.lead":
            phone = record.phone or ""
        if not phone and partner:
            phone = partner.phone or ""
        return self._international(phone, partner) if phone else ""

    def _international(self, phone, partner=False):
        """E.164 when the country is known (phone_validation), else digits with a leading + kept."""
        country = partner.country_id if partner else self.env.company.country_id
        if hasattr(self.env["res.partner"], "_phone_format"):
            formatted = self.env["res.partner"]._phone_format(number=phone, country=country,
                                                               force_format="E164", raise_exception=False)
            if formatted:
                return formatted
        cleaned = re.sub(r"[^\d+]", "", phone or "")
        if cleaned and not cleaned.startswith("+") and country and country.phone_code:
            cleaned = "+%s%s" % (country.phone_code, cleaned.lstrip("0"))
        return cleaned

    @staticmethod
    def _share_link(record):
        if "access_token" not in record._fields or not hasattr(record, "_get_share_url"):
            return ""
        try:
            return record.get_base_url() + record._get_share_url(redirect=True, signup_partner=False)
        except Exception:   # a record type whose portal access is not set up
            return ""

    def _message_for(self, record, partner, link):
        # a contact person of a company is greeted by first name; anyone else (a company, an individual
        # customer) by full name. Odoo 20 derives is_company from the VAT number, so it is not used here.
        if partner and partner.parent_id:
            name = (partner.name or "").split(" ")[0]
        else:
            name = partner.name or "" if partner else ""
        hello = self.env._("Hello %(name)s,", name=name) if name else self.env._("Hello,")
        model = record._name
        if model == "sale.order":
            amount = format_amount(self.env, record.amount_total, record.currency_id)
            if record.state in ("draft", "sent"):
                body = self.env._("here is your quotation %(ref)s for %(amount)s.", ref=record.name, amount=amount)
                if record.validity_date:
                    body += " " + self.env._("It is valid until %(date)s.", date=format_date(self.env, record.validity_date))
            else:
                body = self.env._("here is your order %(ref)s for %(amount)s.", ref=record.name, amount=amount)
        elif model == "account.move" and record.is_invoice():
            amount = format_amount(self.env, record.amount_residual or record.amount_total, record.currency_id)
            if record.move_type in ("out_invoice", "out_refund"):
                body = self.env._("here is invoice %(ref)s for %(amount)s.", ref=record.name, amount=amount)
                if record.invoice_date_due and record.payment_state not in ("paid", "in_payment"):
                    body += " " + self.env._("It is due on %(date)s.", date=format_date(self.env, record.invoice_date_due))
            else:
                body = self.env._("about your bill %(ref)s for %(amount)s.", ref=record.ref or record.name, amount=amount)
        elif model == "purchase.order":
            body = self.env._("here is our purchase order %(ref)s.", ref=record.name)
            if record.date_planned:
                body += " " + self.env._("We expect delivery by %(date)s.", date=format_date(self.env, record.date_planned))
        else:
            body = self.env._("about %(record)s.", record=record.display_name)
        lines = [hello, body]
        if link:
            lines.append(self.env._("You can view it here: %(link)s", link=link))
        signature = self.env.user.name
        if self.env.company.name:
            signature = "%s · %s" % (signature, self.env.company.name)
        lines.append(signature)
        return "\n".join(lines[:2]) + "\n\n" + "\n".join(lines[2:])

    # ------------------------------------------------------------------ action
    def action_open_whatsapp(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            raise UserError(self.env._("This record no longer exists."))
        digits = re.sub(r"\D", "", self.phone or "")
        if len(digits) < 8:
            raise UserError(self.env._("Enter the WhatsApp number in international form, for example +91 98250 12345."))
        if hasattr(record, "message_post"):
            record.message_post(
                body=Markup("<p>%s</p><p>%s</p>") % (
                    self.env._("Shared on WhatsApp with %(phone)s:", phone=self.phone),
                    Markup("<br/>").join((self.message or "").splitlines())),
                message_type="comment", subtype_xmlid="mail.mt_note")
        # a quotation shared with the customer counts as sent, like the email flow
        if record._name == "sale.order" and record.state == "draft" and hasattr(record, "action_quotation_sent"):
            record.action_quotation_sent()
        url = "https://wa.me/%s?text=%s" % (digits, quote(self.message or ""))
        # close the sheet once WhatsApp opens, so the record page refreshes (logged note, new status)
        return {"type": "ir.actions.act_url", "url": url, "target": "new", "close": True}
