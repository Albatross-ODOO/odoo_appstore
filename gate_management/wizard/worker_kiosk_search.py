from odoo import models, fields, api, _

class WorkerKioskSearch(models.TransientModel):
    _name = 'worker.kiosk.search'
    _description = 'Worker Kiosk Search & Check-in'

    worker_id = fields.Many2one(
        'gate.worker', 
        string='Search Worker', 
        help="Search worker by Name or Mobile Number"
    )
    
    # Read-only fields to display worker details
    worker_code = fields.Char(related='worker_id.worker_code', readonly=True)
    worker_type = fields.Selection(related='worker_id.worker_type', readonly=True)
    mobile = fields.Char(related='worker_id.mobile', readonly=True)
    photo = fields.Binary(related='worker_id.photo', readonly=True)
    current_state = fields.Selection(related='worker_id.current_state', readonly=True)

    def action_toggle_attendance(self):
        self.ensure_one()
        if self.worker_id:
            # Trigger check-in/out on the worker record
            self.worker_id.action_toggle_attendance()
            # Clear search so the watchman is ready for the next worker
            self.worker_id = False
            
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'worker.kiosk.search',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }
