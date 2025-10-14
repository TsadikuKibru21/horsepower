from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    quotation_print_limit = fields.Float(
        string="Quotation Amount Limit To Print without Approve",
        config_parameter='custom_sales_warehouse.quotation_print_limit'
    )
