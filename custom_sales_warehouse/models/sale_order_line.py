from odoo import api, fields, models



class SaleOrderLine(models.Model):
    _inherit="sale.order.line"
    sales_from_id = fields.Many2one('sales.from', string='Sales From')
    order_sequence=fields.Char(string="NO")
    default_code=fields.Char(string="Item Code",related="product_id.code")
