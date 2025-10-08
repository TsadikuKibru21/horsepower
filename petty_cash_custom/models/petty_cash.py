# models/petty_cash_custom.py
from odoo import models, fields, api,_
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    petty_cash_id = fields.Many2one('petty.cash.custom', string='Petty Cash')
    
class PettyCashCustom(models.Model):
    _name = 'petty.cash.custom'
    _description = 'Petty Cash Custom'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, copy=False, default=lambda self: _('New'), readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('request', 'Request'),
        ('closed', 'closed')
    ], string='State', default='draft', tracking=True)
    total_amount = fields.Float(string='Total Amount', compute='_compute_total_amount', store=True, tracking=True)
    used_amount = fields.Float(string='Current Used Amount', compute='_compute_used_amount', store=True)
    previous_used_amount = fields.Float(string='Previous Used Amount', compute='_compute_used_amount', store=True)
    remaining_amount = fields.Float(string='Remaining Amount', compute='_compute_remaining_amount', store=True)
    description = fields.Text(string='Description', tracking=True)
    petty_cash_account_id = fields.Many2one('account.account', string='Petty Cash Account', required=True)
    bank_account_id = fields.Many2one('account.account', string='Bank Account')
    
    journal_id=fields.Many2one('account.journal',string="Journal")

    expense_line_ids = fields.One2many('petty.cash.expense.line', 'petty_cash_id', string='Expense Lines')
    previous_expense_line_ids = fields.One2many('previous.petty.cash.expense.line', 'petty_cash_id', string='Previous Expense Lines')
    requester_id=fields.Many2one('res.users',string="Requested By",default=lambda self: self.env.user)
    
    journal_ids = fields.One2many(
        'account.move',
        'petty_cash_id',
        string='Journals',
        compute='_compute_journal_ids',
        readonly=True
    )
    journal_count = fields.Integer(
        string='Journal Entries',
        compute='_compute_journal_count',
        store=False
    )
    def _compute_journal_ids(self):
        for rec in self:
            rec.journal_ids = self.env['account.move'].search([('petty_cash_id', '=', rec.id)])


    def _compute_journal_count(self):
        for rec in self:
            rec.journal_count = len(rec.journal_ids)

    def action_view_journals(self):
        """Open related journal entries"""
        self.ensure_one()
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('petty_cash_id', '=', self.id)],
            'context': {'default_petty_cash_id': self.id},
        }
    @api.depends('petty_cash_account_id')
    def _compute_total_amount(self):
        for record in self:
                _logger.info("################################## aaaaaaaaaaaaaa")
                if record.petty_cash_account_id:
                   
                    _logger.info(record.petty_cash_account_id.current_balance)
                    _logger.info(record.petty_cash_account_id.current_balance)
                    balance = record.petty_cash_account_id.current_balance
                    record.total_amount = balance
                else:
                    record.total_amount = 0.0
                    
    @api.model
    def create(self, vals):
        if vals.get('name', ('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.custom') or _('New')
            res = super(PettyCashCustom, self).create(vals)
            return res

    @api.depends('expense_line_ids.amount','previous_expense_line_ids.amount')
    def _compute_used_amount(self):
        for record in self:
            record.used_amount = sum(record.expense_line_ids.mapped('amount'))
            record.previous_used_amount = sum(record.previous_expense_line_ids.mapped('amount'))

    @api.depends('total_amount', 'used_amount')
    def _compute_remaining_amount(self):
        for record in self:
            record.remaining_amount = record.total_amount - record.used_amount -record.previous_used_amount

    def action_request(self):
        self.state = 'request'

    def action_approve(self):
        # self.state = 'approve'
        # Create initial journal entry: debit petty cash, credit bank
        return {
            'name': 'Petty Cash Refund',
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.refund',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_petty_cash_id': self.id},
        }



    def action_close(self):
        return {
            'name': 'Petty Cash Close',
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.close',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_petty_cash_id': self.id},
        }
        


class PettyCashExpenseLine(models.Model):
    _name = 'petty.cash.expense.line'
    _description = 'Petty Cash Expense Line'

    description = fields.Text(string='Description', required=True)
    date = fields.Date(string='Date', default=fields.Date.today, required=True)
    amount = fields.Float(string='Amount', required=True)
    petty_cash_id = fields.Many2one('petty.cash.custom', string='Petty Cash', required=True, ondelete='cascade')


class PreviousPettyCashExpenseLine(models.Model):
    _name = 'previous.petty.cash.expense.line'
    _description = 'Previous Petty Cash Expense Line'

    description = fields.Text(string='Description', required=True)
    date = fields.Date(string='Date', required=True)
    amount = fields.Float(string='Amount', required=True)
    petty_cash_id = fields.Many2one('petty.cash.custom', string='Petty Cash', required=True, ondelete='cascade')