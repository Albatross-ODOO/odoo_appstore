import re

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class GateWorker(models.Model):
    _name = 'gate.worker'
    _description = 'Workforce Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Worker Name', required=True, tracking=True)
    worker_code = fields.Char(string='Worker ID/Code', required=True, copy=False, index=True)
    worker_type = fields.Selection([
        ('permanent', 'Permanent Employee'),
        ('contract', 'Contractual Worker'),
        ('daily_wage', 'Daily Wage Worker'),
    ], string='Worker Type', default='contract', required=True, tracking=True)

    mobile = fields.Char(string='Mobile Number', tracking=True)
    photo = fields.Binary(string='Worker Photo', attachment=True)
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], default='active', tracking=True)
    current_state = fields.Selection([
        ('outside', 'Outside Premises'),
        ('inside', 'Inside Premises'),
        ('break', 'On Break'),
    ], string='Current Status', compute='_compute_current_state', store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    log_ids = fields.One2many('gate.worker.log', 'worker_id', string='Logs')
    break_ids = fields.One2many('gate.worker.break', 'worker_id', string='Breaks')

    # Import mapping helpers (kept for spreadsheet imports)
    srno = fields.Char(string='SrNo / Worker Code')
    employeename = fields.Char(string='Employee Name')
    employee_phone_number = fields.Char(string='Employee Phone Number')

    _rec_names_search = ['name', 'worker_code', 'mobile', 'employeename', 'employee_phone_number', 'srno']

    _sql_constraints = [('worker_code_uniq', 'unique(worker_code)', 'The Worker Code must be unique!')]

    # ------------------------------------------------------------------
    # Display / search
    # ------------------------------------------------------------------
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
    def _kiosk_search_domain(self, term):
        """Name / code / mobile search, tolerant to phone formatting (last 10 digits)."""
        term = (term or '').strip()
        if not term:
            return []
        subdomains = [[(f, 'ilike', term)] for f in self._rec_names_search]
        digits = ''.join(c for c in term if c.isdigit())
        if len(digits) >= 4:
            short = digits[-10:]
            subdomains += [[('mobile', 'ilike', short)], [('employee_phone_number', 'ilike', short)]]
        domain = []
        for i, sub in enumerate(subdomains):
            domain = sub if i == 0 else ['|'] + domain + sub
        return domain

    # ------------------------------------------------------------------
    # Import aliases
    # ------------------------------------------------------------------
    @api.model
    def _sync_alias_vals(self, vals):
        pairs = (('srno', 'worker_code'), ('employeename', 'name'), ('employee_phone_number', 'mobile'))
        for alias, real in pairs:
            if alias in vals and not vals.get(real):
                vals[real] = vals[alias]
            if real in vals and not vals.get(alias):
                vals[alias] = vals[real]
        return vals

    @api.model
    def _normalize_mobile(self, mobile):
        if not mobile:
            return mobile
        digits = re.sub(r'[^\d+]', '', mobile.strip())
        return digits if digits else mobile

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sync_alias_vals(vals)
            if vals.get('mobile'):
                vals['mobile'] = self._normalize_mobile(vals['mobile'])
        return super().create(vals_list)

    def write(self, vals):
        pairs = (('srno', 'worker_code'), ('employeename', 'name'), ('employee_phone_number', 'mobile'))
        for alias, real in pairs:
            if alias in vals and real not in vals:
                vals[real] = vals[alias]
            if real in vals and alias not in vals:
                vals[alias] = vals[real]
        if vals.get('mobile'):
            vals['mobile'] = self._normalize_mobile(vals['mobile'])
        return super().write(vals)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    @api.depends('log_ids.state', 'log_ids.check_out_time', 'break_ids.end_time')
    def _compute_current_state(self):
        for worker in self:
            log = worker._open_log()
            if not log:
                worker.current_state = 'outside'
            elif worker._open_break(log):
                worker.current_state = 'break'
            else:
                worker.current_state = 'inside'

    def _open_log(self):
        self.ensure_one()
        return self.env['gate.worker.log'].search([
            ('worker_id', '=', self.id), ('state', '=', 'inside')], order='check_in_time desc', limit=1)

    def _open_break(self, log=None):
        self.ensure_one()
        domain = [('worker_id', '=', self.id), ('end_time', '=', False)]
        if log:
            domain.append(('log_id', '=', log.id))
        return self.env['gate.worker.break'].search(domain, order='start_time desc', limit=1)

    def _check_gate_user(self):
        if not self.env.user.has_group('gate_management.group_gate_guard'):
            raise AccessError(_("Only gate users can record worker attendance."))

    # ------------------------------------------------------------------
    # Attendance actions (callable by guards: profile stays read-only for them)
    # ------------------------------------------------------------------
    def action_check_in(self):
        self._check_gate_user()
        now = fields.Datetime.now()
        for worker in self.sudo():
            if worker.status != 'active':
                raise UserError(_("%s is inactive and cannot be checked in.") % worker.name)
            if worker._open_log():
                continue
            self.env['gate.worker.log'].sudo().create({
                'worker_id': worker.id, 'check_in_time': now, 'state': 'inside'})
            self.env['gate.entry'].sudo().create({
                'entry_type': 'worker',
                'operation_type': 'incoming',
                'visitor_name': worker.name,
                'mobile_number': worker.mobile,
                'worker_id': worker.id,
                'company_id': worker.company_id.id or self.env.company.id,
                'check_in_time': now,
                'entry_time': now,
                'state': 'entered',
            })
        return True

    def action_check_out(self):
        self._check_gate_user()
        now = fields.Datetime.now()
        for worker in self.sudo():
            worker._close_open_shift(now)
            entry = self.env['gate.entry'].sudo().search([
                ('worker_id', '=', worker.id), ('state', '=', 'entered')], order='check_in_time desc', limit=1)
            if entry:
                entry.write({'check_out_time': now, 'exit_time': now, 'state': 'exited'})
        return True

    def _close_open_shift(self, now=None):
        """Close the open break (if any) and the open log. Used by check-out and by gate.entry.action_exit."""
        now = now or fields.Datetime.now()
        for worker in self.sudo():
            log = worker._open_log()
            brk = worker._open_break()
            if brk:
                brk.write({'end_time': now})
            if log:
                log.write({'check_out_time': now, 'state': 'outside'})
            else:
                # kept from the original behaviour: a check-out without an open shift still leaves a trace
                self.env['gate.worker.log'].sudo().create({
                    'worker_id': worker.id, 'check_in_time': now, 'check_out_time': now, 'state': 'outside'})

    def action_start_break(self):
        self._check_gate_user()
        now = fields.Datetime.now()
        for worker in self.sudo():
            log = worker._open_log()
            if not log:
                raise UserError(_("%s is not inside the premises.") % worker.name)
            if worker._open_break(log):
                continue
            self.env['gate.worker.break'].sudo().create({
                'worker_id': worker.id, 'log_id': log.id, 'start_time': now})
        return True

    def action_end_break(self):
        self._check_gate_user()
        now = fields.Datetime.now()
        for worker in self.sudo():
            brk = worker._open_break()
            if brk:
                brk.write({'end_time': now})
        return True

    def action_toggle_attendance(self):
        """Kept for backward compatibility (buttons / kanban / automation)."""
        self.ensure_one()
        if self.current_state == 'outside':
            return self.action_check_in()
        return self.action_check_out()

    @api.model
    def action_break_all(self):
        workers = self.search([('current_state', '=', 'inside')])
        workers.action_start_break()
        return len(workers)

    @api.model
    def action_break_over_all(self):
        workers = self.search([('current_state', '=', 'break')])
        workers.action_end_break()
        return len(workers)

    # ------------------------------------------------------------------
    # Data for the Worker Attendance page (OWL client action)
    # ------------------------------------------------------------------
    @api.model
    def kiosk_data(self, term='', limit=200):
        domain = [('status', '=', 'active')] + self._kiosk_search_domain(term)
        workers = self.search(domain, limit=limit)
        Log = self.env['gate.worker.log'].sudo()
        Break = self.env['gate.worker.break'].sudo()
        open_logs = {l.worker_id.id: l for l in Log.search([('worker_id', 'in', workers.ids), ('state', '=', 'inside')], order='check_in_time asc')}
        open_breaks = {b.worker_id.id: b for b in Break.search([('worker_id', 'in', workers.ids), ('end_time', '=', False)], order='start_time asc')}
        tz = fields.Datetime.context_timestamp
        rows = []
        for w in workers:
            log, brk = open_logs.get(w.id), open_breaks.get(w.id)
            rows.append({
                'id': w.id,
                'name': w.name,
                'code': w.worker_code or '',
                'type': dict(self._fields['worker_type'].selection).get(w.worker_type, ''),
                'mobile': w.mobile or '',
                'has_photo': bool(w.photo),
                'state': w.current_state,
                'since': tz(self, log.check_in_time).strftime('%H:%M') if log else '',
                'break_since': tz(self, brk.start_time).strftime('%H:%M') if brk else '',
            })
        counts = {s: self.search_count([('status', '=', 'active'), ('current_state', '=', s)]) for s in ('inside', 'break', 'outside')}
        return {'rows': rows, 'counts': counts}


class GateWorkerLog(models.Model):
    _name = 'gate.worker.log'
    _description = 'Workforce Entry Log'
    _order = 'check_in_time desc'

    worker_id = fields.Many2one('gate.worker', string='Worker', required=True, ondelete='cascade', index=True)
    check_in_time = fields.Datetime(string='Check-in Time', default=fields.Datetime.now)
    check_out_time = fields.Datetime(string='Check-out Time')
    state = fields.Selection([('inside', 'Inside'), ('outside', 'Outside')], string='State', default='inside')
    break_ids = fields.One2many('gate.worker.break', 'log_id', string='Breaks')
    break_minutes = fields.Float(string='Break (min)', compute='_compute_minutes', store=True)
    shift_minutes = fields.Float(string='Shift (min)', compute='_compute_minutes', store=True)

    @api.depends('check_in_time', 'check_out_time', 'break_ids.duration')
    def _compute_minutes(self):
        for log in self:
            log.break_minutes = sum(log.break_ids.mapped('duration'))
            if log.check_in_time and log.check_out_time:
                log.shift_minutes = (log.check_out_time - log.check_in_time).total_seconds() / 60.0
            else:
                log.shift_minutes = 0.0


class GateWorkerBreak(models.Model):
    _name = 'gate.worker.break'
    _description = 'Workforce Break'
    _order = 'start_time desc'

    worker_id = fields.Many2one('gate.worker', string='Worker', required=True, ondelete='cascade', index=True)
    log_id = fields.Many2one('gate.worker.log', string='Shift', ondelete='cascade', index=True)
    start_time = fields.Datetime(string='Break Start', default=fields.Datetime.now, required=True)
    end_time = fields.Datetime(string='Break End')
    duration = fields.Float(string='Duration (min)', compute='_compute_duration', store=True)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for brk in self:
            if brk.start_time and brk.end_time:
                brk.duration = (brk.end_time - brk.start_time).total_seconds() / 60.0
            else:
                brk.duration = 0.0
