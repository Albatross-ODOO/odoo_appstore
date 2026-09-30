from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    gate_address = fields.Text(
        string='Gate / Plant Address',
        help="Address printed on gate passes and visitor invitations, and used for the "
             "Get Directions link. Leave empty to use the company address.",
    )
    gate_maps_url = fields.Char(
        string='Gate Map Link',
        help="Optional Google Maps link pointing at the exact gate. Leave empty to build "
             "a directions link from the address above.",
    )
    gate_auto_exit_hour = fields.Float(
        string='Auto Check-Out Time',
        default=23.98,
        help="Time of day after which a material entry still inside the premises is "
             "automatically checked out.",
    )

    @api.model
    def action_open_gate_settings(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Gate Settings'),
            'res_model': 'res.company',
            'view_mode': 'form',
            'res_id': self.env.company.id,
            'views': [(self.env.ref('gate_management.view_company_form_gate_settings').id, 'form')],
            'target': 'current',
        }
