from odoo import models, fields

class SalesFrom(models.Model):
    _name = 'sales.from'
    _description = 'Sales From'

    name = fields.Char(string='Name', required=True)
    product=fields.Char(string="Product")
    reference=fields.Char(string="Reference")
    quantity=fields.Float(string="Quantity")
    partner_id=fields.Many2one('res.partner',string="Partner")