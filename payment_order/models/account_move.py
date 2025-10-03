from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    
    payment_code = fields.Selection([
        ('cash', 'Cash or Transfer'),
        ('cheque', 'Cheque'),
        ('cpo', 'CPO')
    ], default='cash',track_visibility='always',string="Payment Mode")
    cheque_no=fields.Char(string='Cheque No')
    cpo_no=fields.Char(string='CPO No')
    
    def _create_payment_vals_from_wizard(self,batch_result):
        """Extend to include custom fields in payment values"""
        vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard(batch_result)
        vals.update({
            'payment_code': self.payment_code,
            'cheque_no': self.cheque_no,
            'cpo_no': self.cpo_no,
        })
        return vals
    
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_code = fields.Selection([
        ('cash', 'Cash or Transfer'),
        ('cheque', 'Cheque'),
        ('cpo', 'CPO')
    ], default='cash',track_visibility='always',string="Payment Mode")
    cheque_no=fields.Char(string='Cheque No')
    cpo_no=fields.Char(string='CPO No')

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_type = fields.Selection([
        ('credit_sales', 'Credit Sales'),
        ('cash_sales', 'Cash Sales'),
    ], string='Invoice Type', default=False)

    
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_type = fields.Selection([
        ('credit_sales', 'Credit Sales'),
        ('cash_sales', 'Cash Sales'),
    ], string='Sale Type', default=False)
    
    def _prepare_invoice(self):
        """Extend to pass sale_type to invoice_type"""
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'invoice_type': self.sale_type or False,
        })
        return invoice_vals