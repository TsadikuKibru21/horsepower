from odoo import models, fields,_
from odoo.exceptions import UserError
class PurchaseRequest(models.Model):
    _inherit='purchase.request'



  
    def action_approve(self):
        self.state = 'approved'
        self.approved_by = self.env.user
        self.approved_date = fields.Date.today()

        # Group request lines by vendor
        vendor_lines = {}
        for line in self.request_lines:
            if not line.vendor:
                raise UserError(_("Please set a vendor for all request lines before approval."))
            vendor_lines.setdefault(line.vendor.id, []).append(line)

        # Create Purchase Orders per vendor
        purchase_orders = []
        for vendor_id, lines in vendor_lines.items():
            po_lines = []
            for l in lines:
                po_lines.append((0, 0, {
                    'product_id': l.product_id.id,
                    'product_qty': l.quantity,
                    'price_unit': l.unit_price,
                    'name': l.product_id.display_name,
                    'date_planned': fields.Date.today(),
                    'product_uom': l.uom_id.id,
                    'order_sequence':l.order_sequence,
                }))
            po = self.env['purchase.order'].create({
                'partner_id': vendor_id,
                'order_line': po_lines,
                'ref': self.name,
            })
            # Confirm the Purchase Order
            po.button_confirm()
            purchase_orders.append(po)

            # Create an Advance Payment linked to PO
            self.env['advance.payment'].create({
                'partner_id': vendor_id,
                'amount': sum(l.quantity * l.unit_price for l in lines),
                'advance_type': 'send',  # or 'receive' depending on your flow
                'payment_date': fields.Date.today(),
                'state': 'submitted',
                'memo': _('Payment for PO %s') % po.name,
                'company_id': self.env.company.id,
            })
        
