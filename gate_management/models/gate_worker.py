from odoo import models, fields, api, _
from odoo.osv import expression

class GateWorker(models.Model):
    _name = 'gate.worker'
    _description = 'Workforce Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Worker Name', required=True, tracking=True)
    worker_code = fields.Char(string='Worker ID/Code', required=True, copy=False, index=True)
    worker_type = fields.Selection([
        ('permanent', 'Permanent Employee'),
        ('contract', 'Contractual Worker'),
        ('daily_wage', 'Daily Wage Worker')
    ], string='Worker Type', default='contract', required=True, tracking=True)
    
    mobile = fields.Char(string='Mobile Number', tracking=True)
    photo = fields.Binary(string='Worker Photo', attachment=True)
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], default='active', tracking=True)
    current_state = fields.Selection([
        ('outside', 'Outside Premises'),
        ('inside', 'Inside Premises')
    ], string='Current Status', compute='_compute_current_state', store=True)

    log_ids = fields.One2many('gate.worker.log', 'worker_id', string='Logs')

    # Import mapping helpers
    srno = fields.Char(string='SrNo / Worker Code')
    employeename = fields.Char(string='Employee Name')
    employee_phone_number = fields.Char(string='Employee Phone Number')

    _rec_names_search = ['name', 'worker_code', 'mobile', 'employeename', 'employee_phone_number', 'srno']

    _sql_constraints = [
        ('worker_code_uniq', 'unique(worker_code)', 'The Worker Code must be unique!')
    ]

    @api.depends('name', 'worker_code', 'mobile', 'employeename', 'employee_phone_number', 'srno')
    def _compute_display_name(self):
        for worker in self:
            name = worker.name or worker.employeename or ''
            code = worker.worker_code or worker.srno or ''
            phone = worker.mobile or worker.employee_phone_number or ''
            
            parts = [name]
            if code:
                parts.append(f"({code})")
            if phone:
                parts.append(f"- {phone}")
            worker.display_name = " ".join(parts)

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        domain = domain or []
        if name:
            subdomains = [
                [('name', operator, name)],
                [('mobile', operator, name)],
                [('worker_code', operator, name)],
                [('employeename', operator, name)],
                [('employee_phone_number', operator, name)],
                [('srno', operator, name)],
            ]
            digits = ''.join(c for c in name if c.isdigit())
            if digits and len(digits) >= 4:
                short_digits = digits[-10:] if len(digits) >= 10 else digits
                subdomains.extend([
                    [('mobile', 'ilike', digits)],
                    [('employee_phone_number', 'ilike', digits)],
                    [('mobile', 'ilike', short_digits)],
                    [('employee_phone_number', 'ilike', short_digits)],
                ])
            name_domain = expression.OR(subdomains)
            domain = expression.AND([domain, name_domain])
        return self._search(domain, limit=limit, order=order)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            subdomains = [
                [('name', operator, name)],
                [('mobile', operator, name)],
                [('worker_code', operator, name)],
                [('employeename', operator, name)],
                [('employee_phone_number', operator, name)],
                [('srno', operator, name)],
            ]
            digits = ''.join(c for c in name if c.isdigit())
            if digits and len(digits) >= 4:
                short_digits = digits[-10:] if len(digits) >= 10 else digits
                subdomains.extend([
                    [('mobile', 'ilike', digits)],
                    [('employee_phone_number', 'ilike', digits)],
                    [('mobile', 'ilike', short_digits)],
                    [('employee_phone_number', 'ilike', short_digits)],
                ])
            name_domain = expression.OR(subdomains)
            args = expression.AND([args, name_domain])
        return super(GateWorker, self).name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'srno' in vals and not vals.get('worker_code'):
                vals['worker_code'] = vals['srno']
            if 'worker_code' in vals and not vals.get('srno'):
                vals['srno'] = vals['worker_code']
            
            if 'employeename' in vals and not vals.get('name'):
                vals['name'] = vals['employeename']
            if 'name' in vals and not vals.get('employeename'):
                vals['employeename'] = vals['name']
                
            if 'employee_phone_number' in vals and not vals.get('mobile'):
                vals['mobile'] = vals['employee_phone_number']
            if 'mobile' in vals and not vals.get('employee_phone_number'):
                vals['employee_phone_number'] = vals['mobile']
        return super(GateWorker, self).create(vals_list)

    def write(self, vals):
        if 'srno' in vals and 'worker_code' not in vals:
            vals['worker_code'] = vals['srno']
        if 'worker_code' in vals and 'srno' not in vals:
            vals['srno'] = vals['worker_code']
            
        if 'employeename' in vals and 'name' not in vals:
            vals['name'] = vals['employeename']
        if 'name' in vals and 'employeename' not in vals:
            vals['employeename'] = vals['name']
            
        if 'employee_phone_number' in vals and 'mobile' not in vals:
            vals['mobile'] = vals['employee_phone_number']
        if 'mobile' in vals and 'employee_phone_number' not in vals:
            vals['employee_phone_number'] = vals['mobile']
            
        return super(GateWorker, self).write(vals)

    @api.depends('log_ids.state', 'log_ids.check_out_time')
    def _compute_current_state(self):
        for worker in self:
            latest_log = self.env['gate.worker.log'].search([('worker_id', '=', worker.id)], order='check_in_time desc', limit=1)
            if latest_log and latest_log.state == 'inside':
                worker.current_state = 'inside'
            else:
                worker.current_state = 'outside'

    def action_toggle_attendance(self):
        self.ensure_one()
        if self.current_state == 'outside':
            # Check-in
            self.env['gate.worker.log'].create({
                'worker_id': self.id,
                'check_in_time': fields.Datetime.now(),
                'state': 'inside'
            })
            
            # Create gate.entry of type 'worker'
            self.env['gate.entry'].create({
                'entry_type': 'worker',
                'visitor_name': self.name,
                'mobile_number': self.mobile,
                'worker_id': self.id,
                'check_in_time': fields.Datetime.now(),
                'entry_time': fields.Datetime.now(),
                'state': 'entered'
            })
        else:
            # Check-out
            latest_log = self.env['gate.worker.log'].search([
                ('worker_id', '=', self.id),
                ('state', '=', 'inside')
            ], order='check_in_time desc', limit=1)
            if latest_log:
                latest_log.write({
                    'check_out_time': fields.Datetime.now(),
                    'state': 'outside'
                })
            else:
                self.env['gate.worker.log'].create({
                    'worker_id': self.id,
                    'check_in_time': fields.Datetime.now(),
                    'check_out_time': fields.Datetime.now(),
                    'state': 'outside'
                })
            
            # Find the latest entered gate.entry for this worker and check out
            latest_entry = self.env['gate.entry'].search([
                ('worker_id', '=', self.id),
                ('state', '=', 'entered')
            ], order='check_in_time desc', limit=1)
            if latest_entry:
                latest_entry.write({
                    'check_out_time': fields.Datetime.now(),
                    'exit_time': fields.Datetime.now(),
                    'state': 'exited'
                })


class GateWorkerLog(models.Model):
    _name = 'gate.worker.log'
    _description = 'Workforce Entry Log'
    _order = 'check_in_time desc'

    worker_id = fields.Many2one('gate.worker', string='Worker', required=True, ondelete='cascade')
    check_in_time = fields.Datetime(string='Check-in Time', default=fields.Datetime.now)
    check_out_time = fields.Datetime(string='Check-out Time')
    state = fields.Selection([
        ('inside', 'Inside'),
        ('outside', 'Outside')
    ], string='State', default='inside')
