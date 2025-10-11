from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging


class StockLocation(models.Model):
    _inherit = 'stock.location'

    account_id = fields.Many2one('account.account', string="Chart of Account")
