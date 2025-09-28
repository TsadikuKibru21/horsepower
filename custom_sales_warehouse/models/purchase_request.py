from odoo import models, fields
from odoo.exceptions import UserError
class PurchaseRequest(models.Model):
    _inherit='purchase.request'

    sale_order=fields.Many2one('sale.order')

    project=fields.Char(string="Project")

    def action_create_purchase_order(self):
        
        if not self.vendor_id:
            raise UserError("Please provide a vendor before creating the purchase order.")
        
        config_param = self.env['ir.config_parameter'].sudo()
        max_direct_purchase = float(config_param.get_param('purchase.max_direct_purchase', default=5000))

        # Add validation if total_price > max_direct_purchase and tender_id is empty
        # for line in self.request_lines:
        #     if line.unit_price > max_direct_purchase:
        #         raise ValidationError(f"Costs for {line.product_id.name} are too high for a direct purchase. Please create a tender.")

        self.env['purchase.order'].create({
            'ref': self.name,
            'project':self.project,
            'partner_id': self.vendor_id.id,
            'order_line': [(0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
                'price_unit': line.unit_price,
            }) for line in self.request_lines],
        })

        self.state = 'approved'
    def action_approve(self):
        self.state = 'approved'
        self.approved_by = self.env.user
        self.approved_date = fields.Date.today()
        
        # Create Payment Order
        total_amount = sum(line.subtotal for line in self.request_lines)
        payment_order_vals = {
            'source_from': 'purchase',
            'purchase_ref': self.id,
            'pay_to': self.vendor_id.id,
            'amount': total_amount,
            'purpose': f"Payment for Purchase Request {self.name}",
            'date': fields.Date.today(),
        }
        self.env['payment.order'].create(payment_order_vals)
        

class Purchase(models.Model):
    _inherit='purchase.order'

    project=fields.Char(string="Project")