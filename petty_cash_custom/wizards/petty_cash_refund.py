# wizards/petty_cash_refund.py
from odoo import models, fields, api
from odoo.exceptions import UserError

class PettyCashRefund(models.TransientModel):
    _name = 'petty.cash.refund'
    _description = 'Petty Cash Refund Wizard'

    amount = fields.Float(string='Refund Amount', required=True)
    from_account_id = fields.Many2one('account.account', string='From Account', required=True)
    petty_cash_id = fields.Many2one('petty.cash.custom', string='Petty Cash')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_petty_cash_id'):
            res['petty_cash_id'] = self.env.context['default_petty_cash_id']
            petty_cash = self.env['petty.cash.custom'].browse(res['petty_cash_id'])
            res['amount'] = petty_cash.used_amount  
        return res

    def action_refund(self):
        self.ensure_one()
        petty_cash = self.petty_cash_id
        
        
        # Move current expenses to previous
        for line in petty_cash.expense_line_ids:
            self.env['previous.petty.cash.expense.line'].create({
                'description': line.description,
                'date': line.date,
                'amount': line.amount,
                'petty_cash_id': petty_cash.id,
            })
        petty_cash.expense_line_ids.unlink()
        
        # Update total_amount
        petty_cash.total_amount += self.amount
        petty_cash._compute_remaining_amount()
        
        # Create journal entry: debit from_account (bank), credit petty cash
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': petty_cash.journal_id.id,
            'date': fields.Date.today(),
            'petty_cash_id': petty_cash.id, 
            'ref': f'Petty Cash Refund - {petty_cash.name}',
            'line_ids': [
                (0, 0, {
                    'account_id': petty_cash.petty_cash_account_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'name': 'Petty Cash Refund',
                }),
                (0, 0, {
                    'account_id': self.from_account_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'name': 'Petty Cash Refund',
                }),
            ],
        })
        move.action_post()
        petty_cash.state = 'draft'
        
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    
    
  
class PettyCashClose(models.TransientModel):
    _name = 'petty.cash.close'
    _description = 'Petty Cash Close Wizard'

    remaining_amount = fields.Float(string='Remaining Amount')
    # bank_account_id = fields.Many2one('account.account', string='Bank Account')
    to_account_id = fields.Many2one('account.account', string='To Account', required=True)
    suspended_account_id = fields.Many2one('account.account', string='Suspended Account')
    is_include_remaining_amount = fields.Boolean(string='Include Remaining Amount', default=False)
    total_amount = fields.Float(string='Total Close Amount', compute='_compute_total_amount')
    petty_cash_id = fields.Many2one('petty.cash.custom', string='Petty Cash')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_petty_cash_id'):
            res['petty_cash_id'] = self.env.context['default_petty_cash_id']
            petty = self.env['petty.cash.custom'].browse(res['petty_cash_id'])
            res['remaining_amount'] = petty.remaining_amount
            # res['to_account_id'] = petty.bank_account_id.id
        return res


    @api.depends('is_include_remaining_amount', 'petty_cash_id.total_amount', 'petty_cash_id.used_amount', 'petty_cash_id.previous_used_amount')
    def _compute_total_amount(self):
        for record in self:
            if record.petty_cash_id:
                if record.is_include_remaining_amount:
                    record.total_amount = record.petty_cash_id.total_amount
                else:
                    record.total_amount = record.petty_cash_id.used_amount + record.petty_cash_id.previous_used_amount
            else:
                record.total_amount = 0.0

    def action_close(self):
        self.ensure_one()
        petty_cash = self.petty_cash_id
  
        if not petty_cash.journal_id:
            raise UserError('Please select a journal in the Petty Cash.')
        
        balance = petty_cash.total_amount
        used_total = petty_cash.used_amount + petty_cash.previous_used_amount
        remianing=petty_cash.remaining_amount
        line_ids = []
        if self.is_include_remaining_amount or used_total == balance:
            line_ids = [
                (0, 0, {
                    'account_id': self.to_account_id.id,
                    'debit': balance,
                    'credit': 0.0,
                    'name': 'Petty Cash Close',
                }),
                (0, 0, {
                    'account_id': petty_cash.petty_cash_account_id.id,
                    'debit': 0.0,
                    'credit': balance,
                    'name': 'Petty Cash Close',
                }),
            ]
        else:
            if not self.suspended_account_id:
                raise UserError('Suspended Account is required when not including remaining amount.')
            if not self.to_account_id:
                raise UserError('Bank Account is required when not including remaining amount.')
            line_ids = [
                (0, 0, {
                    'account_id': self.to_account_id.id,
                    'debit': used_total,
                    'credit': 0.0,
                    'name': 'Petty Cash Close',
                }),
                (0, 0, {
                    'account_id': self.suspended_account_id.id,
                    'debit': remianing,
                    'credit': 0.0,
                    'name': 'Petty Cash Close',
                }),
               
                (0, 0, {
                    'account_id': petty_cash.petty_cash_account_id.id,
                    'debit': 0.0,
                    'credit': balance,
                    'name': 'Petty Cash Close - Return Remaining',
                }),
            ]
        
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': petty_cash.journal_id.id,
            'petty_cash_id': petty_cash.id, 
            'date': fields.Date.today(),
            'ref': f'Petty Cash Close - {petty_cash.name}',
            'line_ids': line_ids,
        })
        move.action_post()
        
        # Close the petty cash
        petty_cash.state = 'closed'
        
        return {'type': 'ir.actions.client', 'tag': 'reload'}