from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class StockRoute(models.Model):
    _inherit = 'stock.route'

    is_custom_stock_flow = fields.Boolean(
        string="Use Custom Stock Flow",
        default=False,
        help="If checked, sale orders for products with this route will use the custom stock-checking and purchase order creation logic."
    )
