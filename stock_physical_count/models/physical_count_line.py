# models/physical_count_line.py
from odoo import models, fields, api

class PhysicalCountLine(models.Model):
    _name = 'physical.count.line'
    _description = 'Physical Count Line'
    _order = 'product_id, location_id'

    item_code = fields.Many2one('product.item.code', string="Item Code", ondelete="cascade")
    
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
    
    history_ids = fields.One2many('physical.count.line.history', 'line_id', string='History')
    
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
                quants = self.env['stock.quant'].search([
                    ('product_id','=',record.product_id.id),
                    ('location_id','=',record.location_id.id),
                ])
                record.on_hand_qty = sum(quant.quantity for quant in quants)  # Fixed to sum all quants; adjust to inventory_quantity_auto_apply if custom field
            else:
                record.on_hand_qty = 0.0

    @api.depends('on_hand_qty', 'counted_qty', 'consignment_out', 'project_out', 'damaged')
    def _compute_difference(self):
        for record in self:
            record.difference = record.on_hand_qty - (
                record.counted_qty + record.consignment_out + record.project_out + record.damaged
            )

    @api.model
    def create(self, vals):
        line = super(PhysicalCountLine, self).create(vals)
        line._create_history()
        return line

    def write(self, vals):
        res = super(PhysicalCountLine, self).write(vals)
        self._create_history()
        return res

    def _create_history(self):
        for record in self:
            history_vals = {
                'line_id': record.id,
                'item_code': record.item_code.id if record.item_code else False,
                'product_id': record.product_id.id if record.product_id else False,
                'location_id': record.location_id.id if record.location_id else False,
                'on_hand_qty': record.on_hand_qty,
                'counted_qty': record.counted_qty,
                'consignment_out': record.consignment_out,
                'project_out': record.project_out,
                'damaged': record.damaged,
                'difference': record.difference,
                'remark': record.remark,
            }
            self.env['physical.count.line.history'].create(history_vals)

    def action_view_history(self):
        self.ensure_one()
        return {
            'name': 'History',
            'type': 'ir.actions.act_window',
            'res_model': 'physical.count.line.history',
            'view_mode': 'tree,form',
            'domain': [('line_id', '=', self.id)],
            'context': {'default_line_id': self.id},
        }


class PhysicalCountLineHistory(models.Model):
    _name = 'physical.count.line.history'
    _description = 'Physical Count Line History'
    _order = 'create_date desc'

    line_id = fields.Many2one('physical.count.line', string='Physical Count Line', required=True, ondelete='cascade', readonly=True)
   
    item_code = fields.Many2one('product.item.code', string="Item Code", readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    on_hand_qty = fields.Float(string='On Hand Quantity', digits='Product Unit of Measure', readonly=True)
    counted_qty = fields.Float(string='Counted Quantity', digits='Product Unit of Measure', readonly=True)
    consignment_out = fields.Float(string='Consignment Out', digits='Product Unit of Measure', readonly=True)
    project_out = fields.Float(string='Project Out', digits='Product Unit of Measure', readonly=True)
    damaged = fields.Float(string='Damaged', digits='Product Unit of Measure', readonly=True)
    difference = fields.Float(string='Difference', digits='Product Unit of Measure', readonly=True)
    remark = fields.Text(string='Remark', readonly=True)
    create_date = fields.Datetime(string='Date', readonly=True, default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, readonly=True)