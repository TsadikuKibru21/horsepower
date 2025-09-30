from odoo import api, fields, models



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.name

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.name