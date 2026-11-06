from . import controllers
from . import models


def uninstall_hook(env):
    """Leave nothing behind: the phone-gantt asset records init() creates on Enterprise."""
    env["ir.asset"].sudo().search([("path", "=like", "aic_workspace/%")]).unlink()
