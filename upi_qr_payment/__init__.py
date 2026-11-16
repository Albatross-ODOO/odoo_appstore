from . import models


def upi_qr_post_init(env):
    """The QR always encodes INR: make sure the currency exists and is active."""
    inr = env['res.currency'].with_context(active_test=False).search([('name', '=', 'INR')], limit=1)
    if inr and not inr.active:
        inr.active = True
