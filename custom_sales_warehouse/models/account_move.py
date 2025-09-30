from odoo import api, fields, models



class AccountMoveLine(models.Model):
    _inherit="account.move.line"

    order_sequence=fields.Char(string="NO")
    default_code=fields.Char(string="Item Code",related="product_id.code")
