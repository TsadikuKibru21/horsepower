from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _description = 'Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Name', required=True, copy=False, default=lambda self: _('New'), readonly=True)
    effective_date = fields.Date(string='Date', required=True, default=fields.Date.today())
    request_lines = fields.One2many('purchase.request.line', 'request_id', string='Request Lines')

    approved_by = fields.Many2one('res.users', string="Approved by",  readonly=True, store=True)
    approved_date = fields.Date(string='Approval Date', readonly=True,)
    prepared_by = fields.Many2one('res.users',string="Prepared By")
    prepared_date = fields.Date(string="Prepared Date")
    checked_by = fields.Many2one('res.users', string="Confirmed by",  readonly=True, store=True)
    checked_date = fields.Date(string='Confirmed Date', readonly=True,)

    requester_id=fields.Many2one('res.users',string="Requester Name")

    purchase_order_count = fields.Integer(string='Purchase Order Count', compute='_compute_purchase_order_count')



   

    def _compute_purchase_order_count(self):
        for rec in self:
            rec.purchase_order_count = self.env['purchase.order'].search_count([('ref', '=', rec.name)])

    def purchase_order_action(self):

        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'res_model': 'purchase.order',
            'domain': [('ref', '=', self.name)],
            'view_mode': 'tree,form',
            'target': 'current'
        }

   
    def purchase_tender_action(self):

        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Tender',
            'res_model': 'purchase.tender',
            'domain': [('request_id', '=', self.name)],
            'view_mode': 'tree,form',
            'target': 'current'
        }

    state = fields.Selection([
        ('draft', 'Draft'),
        ('prepared','Prepared'),
        ('confirmed','Confirmed'),
        ('approved', 'Approved'),
       
      
    ], default="draft")

    def action_submit(self):
        self.state = 'prepared'
        self.prepared_by = self.env.user
        self.prepared_date = fields.Date.today()

    def action_confirm(self):
        self.state = 'confirmed'
        self.checked_by=self.env.user.id
        self.checked_date = fields.Date.today()
        # if self.purchase_type == 'direct':
        #     self.action_create_purchase_order()

    def action_approve(self):
        self.state = 'approved'
        self.approved_by = self.env.user
        self.approved_date = fields.Date.today()
        # self.set_product_price()
    
    def set_product_price(self):
        for rec in self:
            for line in rec.request_lines:
                line.product_id.standard_price = line.current_market_price

    def action_validate(self):
        self.state = 'validate'

    def reset_draft(self):
        self.state = 'draft'

    @api.model
    def create(self, vals):
        if vals.get('name', ('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request') or _('New')
            res = super(PurchaseRequest, self).create(vals)
            return res

    def action_create_purchase_order(self):
        if not self.vendor_id:
            raise UserError("Please provide a vendor before creating the purchase order.")
        

        self.env['purchase.order'].create({
            'ref': self.name,
            'partner_id': self.vendor_id.id,
            'order_line': [(0, 0, {
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
                'price_unit': line.unit_price,
            }) for line in self.request_lines],
        })

        self.state = 'approved'

class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _description = 'Purchase Request Line'

    request_id = fields.Many2one('purchase.request', string='Purchase Request')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    sales_price= fields.Float(stiring="Sales Price", related="product_id.list_price")
    unit_price = fields.Float(string="Unit Price") 
    uom_id = fields.Many2one('uom.uom', related="product_id.uom_po_id")
    remark = fields.Char(string="Remark")
    current_market_price= fields.Float(string="Current Price", default=lambda self: self.unit_price, copy=False)
    total_sales_price= fields.Float(string="Total Sales Price", compute="_set_sales_total",store=True)
    subtotal= fields.Float(string="Total Sales Price", compute="_set_subtotal",store=True)
    vendor = fields.Many2one('res.partner',string="Vendor")

    @api.depends('unit_price','quantity')
    def _set_subtotal(self):
        for rec in self:
            rec.subtotal = rec.quantity * rec.unit_price
    
    @api.depends('quantity','unit_price')
    def _set_sales_total(self):
        for rec in self:
            rec.total_sales_price = rec.quantity * rec.unit_price
    

    @api.depends('current_market_price')
    def _set_product_price(self):
        for record in self:
            record.product_id.standard_price = record.current_market_price

  
class PurchaseOrder(models.Model):

    _inherit="purchase.order"
    ref=fields.Char(string="REF")