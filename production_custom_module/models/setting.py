from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inventory_valuation_journal_id = fields.Many2one(
        'account.journal',
        string="Inventory Valuation Journal",
        config_parameter='production_custom_module.inventory_valuation_journal_id'
    )
