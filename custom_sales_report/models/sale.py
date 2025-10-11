from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit="sale.order"
    
    quotation_description=fields.Text(string="Quotation Description") 
    
    last_followup_date = fields.Date(string="Last Follow-up Date",default=fields.Date.today())
 
class SaleOrderLine(models.Model):
    _inherit="sale.order.line"
    commission_percent = fields.Float(string='Commission Percent',related="product_id.commission_percent" ,help='Commission percentage for this product')


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