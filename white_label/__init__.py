from . import controllers
from . import models
from odoo.exceptions import ValidationError


def pre_init_check(cr):
    from odoo.service import common
    version_info = common.exp_version()
    server_serie = version_info.get('server_serie')
    if server_serie != '17.0': raise ValidationError(
        'Module support Odoo series 17.0, found {}, Consider acquiring the appropriate version through a purchase if necessary..'.format(
            server_serie))
    return True
