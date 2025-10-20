from odoo import api, fields, models



class StockMove(models.Model):
    _inherit="stock.move"
    
    default_code = fields.Many2one('product.item.code', string="Item Code",ondelete="cascade")
    
    @api.onchange('default_code')
    def _onchange_default_code(self):
        if self.default_code:
            self.product_id = self.default_code.product_id
        else:
            self.product_id = False
            self.default_code = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.default_code = self.product_id.item_code_id
        else:
            self.default_code = False
