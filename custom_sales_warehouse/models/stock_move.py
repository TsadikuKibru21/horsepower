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
            self.name = self.product_id.name
        else:
            self.default_code = False
            
    
    @api.model
    def create(self, vals):
        # If default_code is set, update product_id
        if vals.get('default_code'):
            item_code = self.env['product.item.code'].browse(vals['default_code'])
            if item_code and item_code.product_id:
                vals['product_id'] = item_code.product_id.id

        # If product_id is set, update default_code
        elif vals.get('product_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            if product and product.item_code_id:
                vals['default_code'] = product.item_code_id.id

        return super(StockMove, self).create(vals)

    def write(self, vals):
        for record in self:
            # If default_code changed, update product_id
            if 'default_code' in vals:
                if vals['default_code']:
                    item_code = self.env['product.item.code'].browse(vals['default_code'])
                    vals['product_id'] = item_code.product_id.id if item_code and item_code.product_id else False
                else:
                    vals['product_id'] = False

            # If product_id changed, update default_code
            elif 'product_id' in vals:
                if vals['product_id']:
                    product = self.env['product.product'].browse(vals['product_id'])
                    vals['default_code'] = product.item_code_id.id if product and product.item_code_id else False
                else:
                    vals['default_code'] = False

        return super(StockMove, self).write(vals)
