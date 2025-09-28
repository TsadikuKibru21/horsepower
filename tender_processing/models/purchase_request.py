from odoo import models,fields,api,_
from odoo.exceptions import ValidationError,UserError
import logging
_logger = logging.getLogger(__name__)
class PurchaseRequest(models.Model):
    _inherit="purchase.request"

    tenderprocess_lines= fields.One2many('tender.process','purchase_request')
    tender_computed = fields.Boolean(default=False)

    def create_purchase_tender(self):
        self.state="tender"
    def compute_winners(self):
        for purchase_request in self:
            purchase_request.tenderprocess_lines.write({'is_winner': False})

            product_tenders = {}
            for tender in purchase_request.tenderprocess_lines:
                product_id = tender.product.id
                if product_id not in product_tenders:
                    product_tenders[product_id] = []
                product_tenders[product_id].append(tender)

            for product_id, tenders in product_tenders.items():
                if tenders:
                    winner = min(tenders, key=lambda x: x.total_price)
                    winner.set_winner()
                    pr_line =self.env['purchase.request.line'].search(
                        [
                            ('product_id','=',product_id),
                            ('request_id','=',purchase_request.id)
                         ], limit=1
                    )
                    pr_line.vendor = winner.vendor.id
                    pr_line.current_market_price = winner.price
            purchase_request.tender_computed=True

    def create_po(self):
        # create PO for each of the tender process lines
        _logger.info("*** in ")
        if not self.tenderprocess_lines:
            raise ValidationError(f"Please add tender process lines.")
        po_count=0
        vendor_count=0
        for rec in self:
            for line in rec.tenderprocess_lines:
                _logger.info(f"*** line is winner: {line.is_winner}")
                if line.is_winner:
                    _logger.info(f"*** line {line.name}")
                    prev_po = self.env['purchase.order'].search([('ref','=',self.name),('partner_id','=',line.vendor.id)],limit=1)
                    
                    if prev_po:
                        _logger.info(f"*** Prev PO {prev_po.name}")

                        self.env['purchase.order.line'].create({
                            'product_id':line.product.id,
                            'product_qty':line.quantity,
                            'order_id':prev_po.id
                        })
                    else:
                        po = self.env['purchase.order'].create({
                            'partner_id': line.vendor.id,
                            'ref':self.name
                        })
                        _logger.info(f"*** New PO {prev_po.name}")
                        self.env['purchase.order.line'].create({
                            'product_id':line.product.id,
                            'product_qty':line.quantity,
                            'order_id':po.id
                        })
                        po_count+=1
                        vendor_count+=1

                        _logger.info(f"*** {po_count} -- {vendor_count}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f'Created {po_count} Purchase orders to {vendor_count} vendors.'),
                'type': 'success', 
                'sticky': False,    
            }
        }
    
    def action_confirm(self):
        if not self.tenderprocess_lines and not self.purchase_type == 'direct' :
            raise ValidationError("No Vendor participated for the bid!!")
        
        return super().action_confirm()


