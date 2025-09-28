from odoo import models, fields, api
from num2words import num2words

class PaymentOrder(models.Model):
    _name = 'payment.order'
    _description = 'Payment Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    source_from=fields.Selection([
        ('purchase','Purchase'),
        ('other','Other'),
    ],default=False,string="Source",tracking=True)
    purchase_ref=fields.Many2one('purchase.request',string="Purchase Reference",tracking=True)
    other_ref=fields.Char(string="Other Reference",tracking=True)
    name = fields.Char(string="Reference", copy=False,default="New")
    location = fields.Char(string="Location",tracking=True)
    date = fields.Date(string="Date", default=fields.Date.today,tracking=True)
    pay_to = fields.Many2one('res.partner',string="Pay To",tracking=True)
    amount = fields.Float(string="Amount",tracking=True)
    amount_in_words = fields.Char(string="Amount in Words", compute='_compute_amount_in_words')
    purpose = fields.Char(string="Purpose",tracking=True)
    activity_code = fields.Char(string="Activity Code",tracking=True)
    source_fund = fields.Char(string="Source Fund",tracking=True)
    account = fields.Char(string="Account",tracking=True)
    budget_for = fields.Float(string="Budget For",tracking=True)
    actual_used = fields.Float(string="Actual Used", readonly=True)
    remaining_balance = fields.Float(string="Remaining Balance", compute='_compute_remaining_balance')
    cpv_count=fields.Integer(string="CPV",compute="compute_cpv_count")
    budget_forward = fields.Float(string="Budget Forward",tracking=True)
    cpv=fields.Many2one('cheque.payment.voucher')
    ref_no_crv = fields.Char(string="Ref. No CRV",tracking=True,related='cpv.name')
    prepared_by = fields.Many2one('res.users', string="Prepared By")
    prepared_date=fields.Date(string="Prepared Date")
    checked_by = fields.Many2one('res.users', string="Checked By")
    checked_date=fields.Date(string="Checked Date")
    approved_by = fields.Many2one('res.users', string="Approved By")
    approved_date=fields.Date(string="Approved Date")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('prepared', 'Prepared'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
        ('cpv_created', 'CPV Created')
    ], string="State", default='draft')

    can_edit_approver = fields.Boolean(
        string='Can Edit in Approver',
        compute='_compute_can_edit_approver',
        store=False,
    )
    def compute_cpv_count(self):
        for rec in self:
            rec.cpv_count=len(self.env['cheque.payment.voucher'].search([
                ('payment_order_id','=',rec.id)
            ]))
    def action_view_cpv(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'CPV',
            'res_model': 'cheque.payment.voucher',
            'view_mode': 'tree,form',
            'domain': [('payment_order_id', '=', self.id)],
            'context': {
                'default_payment_order_id': self.id,
            },
        }

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('payment.order') or 'New'

    

        return super(PaymentOrder, self).create(vals)
    @api.depends('state')
    def _compute_can_edit_approver(self):
        for record in self:
            record.can_edit_approver = (
                record.state == 'approved' and
                self.env.user.has_group('payment_order_and_cpv.group_payment_order_approve')
            )

    @api.depends('amount')
    def _compute_amount_in_words(self):
        for record in self:
            if record.amount:
                record.amount_in_words = num2words(record.amount, lang='en').capitalize() + ' Birr only'
            else:
                record.amount_in_words = ''

    @api.depends('budget_for', 'actual_used')
    def _compute_remaining_balance(self):
        for record in self:
            record.remaining_balance = record.budget_for - record.actual_used

    def action_prepare(self):
        self.write({'state': 'prepared','prepared_date':fields.Date.today(),'prepared_by':self.env.user})
    def action_check(self):
        self.write({'state': 'checked','checked_date':fields.Date.today(),'checked_by':self.env.user})
    def action_approve(self):
        self.write({'state': 'approved','approved_date':fields.Date.today(),'approved_by':self.env.user})
    def action_create_cpv(self):
        cpv = self.env['cheque.payment.voucher'].create({
            # 'name':self.name,
            'payment_order_id': self.id,
            'pay_to': self.pay_to.id,
            'amount': self.amount,
            'amount_in_words': self.amount_in_words,
            'purpose': self.purpose,
            'date': self.date,
            'location': self.location,
        })
        self.cpv=cpv.id
        self.state='cpv_created'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cheque.payment.voucher',
            'view_mode': 'form',
            'res_id': cpv.id,
            'target': 'current',
        }

class ChequePaymentVoucher(models.Model):
    _name = 'cheque.payment.voucher'
    _description = 'Cheque Payment Voucher'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Reference",default="New", copy=False)
    payment_order_id = fields.Many2one('payment.order', string="Payment Order")
    location = fields.Char(string="Location",tracking=True)
    date = fields.Date(string="Date", default=fields.Date.today)
    pay_to = fields.Many2one('res.partner',string="Pay To",tracking=True)
    amount = fields.Float(string="Amount")
    amount_in_words = fields.Char(string="Amount in Words", compute='_compute_amount_in_words')
    purpose = fields.Char(string="Purpose",tracking=True)
    cheque_no = fields.Char(string="Cheque No",tracking=True)
    bank_acc_no = fields.Char(string="Bank Account No",tracking=True)
    prepared_by = fields.Many2one('res.users', string="Prepared By")
    prepared_date=fields.Date(string="Prepared Date")

    checked_by = fields.Many2one('res.users', string="Checked By")
    checked_date=fields.Date(string="Checked Date")
    approved_by = fields.Many2one('res.users', string="Approved By")
    approved_date=fields.Date(string="Approved Date")
    pad_no=fields.Char(string="PAD NO",tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
         ('prepared', 'Prepared'),
        ('checked', 'Checked'),
        ('approved', 'Approved'),
        ('journal_entry_created', 'Journal Entry Created')
    ], string="State", default='draft')

    can_edit_approver = fields.Boolean(
        string='Can Edit in Approver',
        compute='_compute_can_edit_approver',
        store=False,
    )
    journal_count=fields.Integer(string="Journal",compute="compute_journal_count")
    journal=fields.Many2one('account.move',string="Journal")
    line_ids = fields.One2many('cheque.payment.voucher.line', 'voucher_id', string="Lines")
    n_o=fields.Char(string="No")

    @api.depends('journal')
    def compute_journal_count(self):
        for record in self:
            record.journal_count=len(self.env['account.move'].search([
                ('cheque_payment_voucher_id','=',record.id)
            ]))
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('cheque.payment.voucher') or 'New'

    

        return super(ChequePaymentVoucher, self).create(vals)


    def action_view_journal(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'CPV',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', '=', self.journal.id)],
            'context': {
                'default_cheque_payment_voucher_id': self.id,
            },
        }
    @api.depends('state')
    def _compute_can_edit_approver(self):
        for record in self:
            record.can_edit_approver = (
                record.state == 'approved' and
                self.env.user.has_group('payment_order_and_cpv.group_cpv_approve')
            )

    @api.depends('amount')
    def _compute_amount_in_words(self):
        for record in self:
            if record.amount:
                record.amount_in_words = num2words(record.amount, lang='en').capitalize() + ' Birr only'
            else:
                record.amount_in_words = ''

    def action_prepare(self):
        self.write({'state': 'prepared','prepared_date':fields.Date.today(),'prepared_by':self.env.user})
    def action_check(self):
        self.write({'state': 'checked','checked_date':fields.Date.today(),'checked_by':self.env.user})
    def action_approve(self):
        self.write({'state': 'approved','approved_date':fields.Date.today(),'approved_by':self.env.user})

    def action_create_journal_entry(self):
        journal_entry = self.env['account.move'].create({
            'move_type': 'entry',
            'date': self.date,
            'cheque_payment_voucher_id': self.id,
        })
        self.write({
            'state': 'journal_entry_created',
            'journal': journal_entry.id
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_id': journal_entry.id,
            'target': 'current',
            'context': {
                'default_move_type': 'entry',
                'default_date': self.date,
                'default_cheque_payment_voucher_id': self.id,
            },
        }

class ChequePaymentVoucherLine(models.Model):
    _name = 'cheque.payment.voucher.line'
    _description = 'Cheque Payment Voucher Line'

    voucher_id = fields.Many2one('cheque.payment.voucher', string="Voucher", ondelete='cascade')
    account_no = fields.Char(string="Account No")
    description = fields.Char(string="Description")
    debit = fields.Float(string="Debit")
    credit = fields.Float(string="Credit")


class AccountMove(models.Model):
    _inherit = 'account.move'

    cheque_payment_voucher_id = fields.Many2one('cheque.payment.voucher', string="Cheque Payment Voucher")

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self:
            if move.cheque_payment_voucher_id and move.line_ids:
                # Clear existing voucher lines
                move.cheque_payment_voucher_id.line_ids.unlink()
                # Create new voucher lines based on journal lines
                for line in move.line_ids:
                    move.cheque_payment_voucher_id.line_ids.create({
                        'voucher_id': move.cheque_payment_voucher_id.id,
                        'account_no': line.account_id.code,
                        'description': line.name,
                        'debit': line.debit,
                        'credit': line.credit,
                    })
                move.cheque_payment_voucher_id.payment_order_id.write({'actual_used': move.amount_total})
        return res