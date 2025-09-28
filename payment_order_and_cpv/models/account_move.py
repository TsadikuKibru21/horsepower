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

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        compute='_compute_journal_id', inverse='_inverse_journal_id', store=True, readonly=False, precompute=True,
        required=True,
        check_company=True,

        domain="[]"
    )
    