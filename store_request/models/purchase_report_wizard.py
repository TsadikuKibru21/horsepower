from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class PurchaseReportWizard(models.Model):
    _name = 'purchase.order.report'
    _description = 'Purchase Report Wizard'

    date_start = fields.Date(string='Start Date', required=True, default=fields.Date.today)
    date_end = fields.Date(string='End Date', required=True, default=fields.Date.today)
    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase Orders', readonly=True, compute="_get_purchase_orders")
    @api.depends('date_start', 'date_end')
    def _get_purchase_orders(self):
        for record in self:
            purchase_orders = self.env['purchase.order'].search([
                ('date_order', '>=', record.date_start),
                ('date_order', '<=', record.date_end),
                ('state', 'in', ['done','purchase']),
            ])
            record.purchase_order_ids = purchase_orders

    def get_purchase_orders(self):
        self.ensure_one()
        return self.env['purchase.order'].search([
            ('date_order', '>=', self.date_start),
            ('date_order', '<=', self.date_end),
            ('state', 'in', ['done','purchase']),

        ])