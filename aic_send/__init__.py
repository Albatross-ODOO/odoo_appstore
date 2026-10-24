from . import models
from . import wizard


def uninstall_hook(env):
    """Leave nothing behind: the Share on WhatsApp switch."""
    env["ir.config_parameter"].sudo().search([("key", "=like", "aic_send.%")]).unlink()
