from odoo import models, fields, api

class PhysicalCountLine(models.Model):
    _name = 'physical.count.line'
    _description = 'Physical Count Line'
    _order = 'product_id, location_id'

    item_code = fields.Many2one('product.item.code', string="Item Code",ondelete="cascade")
    
    product_id = fields.Many2one('product.product', string='Product', required=True)
    location_id = fields.Many2one('stock.location', string='Location', required=True)
    on_hand_qty = fields.Float(
        string='On Hand Quantity',
        digits='Product Unit of Measure',
        compute='_compute_on_hand_qty',
        readonly=True,
        help="Computed quantity available for the product at the specified location"
    )
    counted_qty = fields.Float(string='Counted Quantity', digits='Product Unit of Measure', default=0.0)
    consignment_out = fields.Float(string='Consignment Out', digits='Product Unit of Measure', default=0.0)
    project_out = fields.Float(string='Project Out', digits='Product Unit of Measure', default=0.0)
    damaged = fields.Float(string='Damaged', digits='Product Unit of Measure', default=0.0)
    difference = fields.Float(
        string='Difference',
        digits='Product Unit of Measure',
        compute='_compute_difference',
        store=True,
        help="On Hand Quantity - (Counted Quantity + Consignment Out + Project Out + Damaged)"
    )
    remark = fields.Text(string='Remark')
    
    @api.onchange('item_code')
    def _onchange_item_code(self):
        if self.item_code:
            self.product_id = self.item_code.product_id
        else:
            self.product_id = False
            self.item_code = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.item_code = self.product_id.item_code_id
        else:
            self.item_code = False

    @api.depends('product_id', 'location_id')
    def _compute_on_hand_qty(self):
        for record in self:
            if record.product_id and record.location_id:
                on_hand_qty = self.env['stock.quant'].search([
                    ('product_id','=',record.product_id.id),
                    ('location_id','=',record.location_id.id),
                ],limit=1)
                record.on_hand_qty=on_hand_qty.inventory_quantity_auto_apply
            else:
                record.on_hand_qty = 0.0

    @api.depends('on_hand_qty', 'counted_qty', 'consignment_out', 'project_out', 'damaged')
    def _compute_difference(self):
        for record in self:
            record.difference = record.on_hand_qty - (
                record.counted_qty + record.consignment_out + record.project_out + record.damaged
            )