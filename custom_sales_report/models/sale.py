from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit="sale.order"
    
    quotation_description=fields.Text(string="Quotation Description") 
    
    estimated_profit = fields.Float(string='Estimated Profit', compute='_compute_estimated_profit', store=True)

    @api.depends('order_line.price_subtotal', 'order_line.product_uom_qty', 'order_line.product_id.standard_price')
    def _compute_estimated_profit(self):
        for record in self:
            total_cost = 0.0
            for line in record.order_line:
                if line.product_id:
                    total_cost += line.product_uom_qty * line.product_id.standard_price
            record.estimated_profit = record.amount_untaxed - total_cost
            

class ProductProduct(models.Model):
    _inherit = 'product.product'

    commission_percent = fields.Float(string='Commission Percent', default=0.0, help='Commission percentage for this product')
    
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    commission_percent = fields.Float(string='Commission Percent', default=0.0, help='Commission percentage for this product')
    
    
    
    
    

    def write(self, vals):
            res = super(ProductTemplate, self).write(vals)
            if 'commission_percent' in vals:
                for template in self:
                    template.product_variant_ids.write({'commission_percent': vals['commission_percent']})
            return res

    @api.model
    def create(self, vals):
        template = super(ProductTemplate, self).create(vals)
        if 'commission_percent' in vals:
            template.product_variant_ids.write({
                'commission_percent': vals['commission_percent']
            })
        return template