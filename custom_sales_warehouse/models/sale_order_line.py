from odoo import api, fields, models



class SaleOrderLine(models.Model):
    _inherit="sale.order.line"
    sales_from_id = fields.Many2one('sales.from', string='Sales From')
    order_sequence=fields.Char(string="NO")
    default_code = fields.Many2one('product.item.code', string="Item Code",ondelete="cascade")
    
   
    
    @api.model
    def create(self, vals):
        if 'product_id' in vals and vals.get('product_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            if product.item_code_id:
                vals['default_code'] = product.item_code_id.id
        if 'default_code' in vals and vals.get('default_code'):
            code = self.env['product.item.code'].browse(vals['default_code'])
            if not code.exists():
                vals['default_code'] = False
        return super(SaleOrderLine, self).create(vals)

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