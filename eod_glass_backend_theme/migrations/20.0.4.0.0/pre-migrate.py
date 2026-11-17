# -*- coding: utf-8 -*-
"""Upgrading from the six-module EOD package: adopt it (upgrade.py). Pre-migrate scripts run before Odoo imports the
module, so the shared code is loaded from its file."""
import importlib.util
import os


def migrate(cr, version):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, "upgrade.py")
    spec = importlib.util.spec_from_file_location("eod_glass_backend_theme_upgrade", path)
    upgrade = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upgrade)
    upgrade.adopt_package(cr)
