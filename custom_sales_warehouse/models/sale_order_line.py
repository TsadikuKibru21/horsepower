from odoo import api, fields, models



class SaleOrderLine(models.Model):
    _inherit="sale.order.line"

    order_sequence=fields.Char(string="NO")
