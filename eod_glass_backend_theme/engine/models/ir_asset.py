# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# ir.asset records named "aic_lock: ..." remove a shared module's own files from the backend bundles. They are
# active while no look is installed: the shared modules (Workspace, Home and Focus) are sold with a look, so on
# their own they add nothing to the web client.
LOCK_PREFIX = "aic_lock:"


class IrAsset(models.Model):
    _inherit = "ir.asset"

    def _register_hook(self):
        super()._register_hook()
        self._aic_sync_lock()

    @api.model
    def _aic_sync_lock(self):
        """Lock records on when no look is installed, off when one is. Runs at every registry load, so installing
        or removing a look (both reload the registry) flips them; writes only when something changes."""
        locked = not self.env["res.company"]._aic_look_installed()
        records = self.sudo().with_context(active_test=False).search([("name", "=like", LOCK_PREFIX + "%")])
        todo = records.filtered(lambda r: r.active != locked)
        if todo:
            todo.write({"active": locked})
            _logger.info("aic_theme: shared modules %s (%d asset rules)", "locked: no look installed" if locked else "unlocked", len(todo))
