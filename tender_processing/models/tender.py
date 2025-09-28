from odoo import models,fields,api,_
from odoo.exceptions import ValidationError,UserError
import logging
_logger = logging.getLogger(__name__)


class TenderProcess(models.Model):
    _name="tender.process"


    name= fields.Char(string="Reference",default="New")
    purchase_request  = fields.Many2one('purchase.request', string="Source")
    vendor = fields.Many2one('res.partner', string="Vendor")
    product = fields.Many2one('product.product',string="Product", )
    prod_domain = fields.Many2many('product.product',compute="_products_domain",store=False)
    uom = fields.Many2one('uom.uom',string="UOM")
    quantity = fields.Float(string="Quantity")
    price= fields.Float(string="Unit Price")
    total_price = fields.Float(string="Total", compute='_get_total')
    is_winner = fields.Boolean(string="Winner")


    @api.depends('price','quantity')
    def _get_total(self):
        for rec in self:
            rec.total_price = rec.price * rec.quantity

    def set_winner(self):
        for rec in self:
            rec.is_winner=True 


    @api.onchange('purchase_request')
    def _products_domain(self):
        if not self.purchase_request:
            
            return [('id', '=', False)] 
        
        self.prod_domain = [line.product_id.id for line in self.purchase_request.request_lines if line.product_id]
        