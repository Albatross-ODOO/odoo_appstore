from . import controllers
from . import models
from . import wizard


def uninstall_hook(env):
    """Leave nothing behind: the start-screen switch."""
    env["ir.config_parameter"].sudo().search([("key", "=like", "aic_home.%")]).unlink()
