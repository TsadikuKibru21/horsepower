from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

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