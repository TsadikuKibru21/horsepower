from odoo import api, fields, models


class ProductCode(models.Model):
    _name = 'product.item.code'
    _rec_name = 'default_code'

    default_code = fields.Char(string="Item Code", required=True)
    product_id = fields.Many2one('product.product', string="Product",ondelete="cascade")