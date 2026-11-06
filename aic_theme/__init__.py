from . import models
from .migrate_legacy import migrate_from_slate


def pre_init_hook(env):
    """A database upgraded from the pre-engine Slate modules: move their data onto the engine first."""
    migrate_from_slate(env.cr)


def uninstall_hook(env):
    """Leave nothing behind: the Community dark-mode asset records init() creates and the theme switch."""
    env["ir.asset"].sudo().search([("path", "=like", "aic_theme/%")]).unlink()
    env["ir.config_parameter"].sudo().search([("key", "=like", "aic_theme.%")]).unlink()
