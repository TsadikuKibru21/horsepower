from odoo import api, fields, models



class PurchaseOrderLine(models.Model):
    _inherit="purchase.order.line"

    order_sequence=fields.Char(string="NO")
    default_code=fields.Char(string="Item Code",related="product_id.code")
