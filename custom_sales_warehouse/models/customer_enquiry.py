from odoo import models, fields, api

class CustomerEnquiry(models.Model):
    _name = 'customer.enquiry'
    _description = 'Customer Enquiry'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    optional_product=fields.Char(string="Optional Product")
    quantity=fields.Float(string="Quantity")
    date = fields.Date(string='Date', default=fields.Date.today, required=True)
    salesperson_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    enquiry_ids = fields.One2many('customer.enquiry', 'partner_id', string='Customer Enquiries')