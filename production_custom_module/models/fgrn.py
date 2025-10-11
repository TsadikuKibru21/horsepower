from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class FGRN(models.Model):
    _name = 'fgrn.return'
    _description = 'Finished Good Return'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="Reference", copy=False, readonly=True, default="New")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse",  track_visibility="always")
    source_location_id = fields.Many2one('stock.location', string="Source Location", domain="[('warehouse_id', '=', warehouse_id)]", track_visibility="always")
    destination_location_id = fields.Many2one('stock.location', string="Destination Location", domain="[('warehouse_id', '=', warehouse_id)]", track_visibility="always")
    store_issue_ids = fields.Many2many('store.request', string="Store Issues", track_visibility="always")
    overhead_cost = fields.Float(string="Overhead Cost", default=0.0)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'), 
        ('validated', 'Validated')
    ], string="State", default='draft', track_visibility='always')
    divided_by = fields.Selection([
        ('equal', 'By Equal'),
        ('quantity', 'By Quantity'), 
        ('weight', 'By Weight')
    ], string="Divided By", default='equal', track_visibility="always")
    total_cost = fields.Float(string="Total Cost", compute='_compute_total_cost', store=True)
    bill_of_material_lines = fields.One2many('fgrn.bom.line', 'fgrn_id', string="Bill of Material Lines")
    submitted_date = fields.Date(string="Submitted Date", readonly=True)
    validated_date = fields.Date(string="Validated Date", readonly=True)
    picking_id = fields.Many2one('stock.picking', string="Transfer", readonly=True)
    journal_id = fields.Many2one('account.move', string="Journal", readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('fgrn.return') or 'New'
        return super(FGRN, self).create(vals)

    @api.depends('store_issue_ids', 'store_issue_ids.voucher_lines', 'overhead_cost')
    def _compute_total_cost(self):
        for record in self:
            total = 0.0
            if record.store_issue_ids:
                for issue in record.store_issue_ids:
                    for line in issue.voucher_lines:
                        total += line.quantity * line.cost
            record.total_cost = total + record.overhead_cost

    @api.onchange('store_issue_ids')
    def _onchange_store_issue_ids(self):
        """Automatically load products, quantities, and costs from selected store issues"""
        self.bill_of_material_lines = False
        if self.store_issue_ids:
            bom_lines = []
            for store_issue in self.store_issue_ids:
                for line in store_issue.voucher_lines:
                    bom_line_vals = {
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'cost': line.cost,
                        'store_issue_id': store_issue.id,
                        'original_store_line_id': line.id,
                    }
                    bom_lines.append((0, 0, bom_line_vals))
            self.bill_of_material_lines = bom_lines

    def action_submit(self):
        self.write({
            'state': 'submitted',
            'submitted_date': fields.Date.today()
        })

    # def action_validate(self):
    #     if not self.source_location_id or not self.destination_location_id:
    #         raise ValidationError("Source and Destination locations are required.")
        
    #     if not self.bill_of_material_lines:
    #         raise ValidationError("No bill of material lines available.")
        
    #     # Create stock transfer
    #     self._create_stock_transfer()
        
    #     # Create accounting entry
    #     self._create_accounting_entry()
        
    #     # Update product costs based on divided_by method
    #     self._update_product_costs()
        
    #     self.write({
    #         'state': 'validated',
    #         'validated_date': fields.Date.today()
    #     })
    def action_validate(self):
        if not self.source_location_id or not self.destination_location_id:
            raise ValidationError("Source and Destination locations are required.")
        
        if not self.bill_of_material_lines:
            raise ValidationError("No bill of material lines available.")
        
        # Validate remaining cost before proceeding
        for store_issue in self.store_issue_ids:
            requested_cost = sum(line.quantity * line.cost for line in self.bill_of_material_lines if line.store_issue_id.id == store_issue.id)
            if requested_cost > store_issue.remaining_cost:
                raise ValidationError(
                    f"Cannot validate: Insufficient remaining cost in store issue {store_issue.name}. "
                    f"Requested: {requested_cost}, Remaining: {store_issue.remaining_cost}"
                )
            
        
        # Create stock transfer
        self._create_stock_transfer()
        
        # Create accounting entry
        self._create_accounting_entry()
        
        # Update product costs based on divided_by method
        self._update_product_costs()
        
        # Update remaining_cost on related store requests
        for store_issue in self.store_issue_ids:
            store_issue._compute_remaining_cost()
        
        self.write({
            'state': 'validated',
            'validated_date': fields.Date.today()
        })

    def _create_stock_transfer(self):
        """Create stock picking for quantity transfer"""
        stock_moves = []
        for line in self.bill_of_material_lines:
            if line.quantity > 0:
                stock_move_vals = {
                    'name': f"FGRN {self.name} - {line.product_id.name}",
                    'product_id': line.product_id.id,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uom_qty': line.quantity,
                    'origin': self.name,
                    'location_id': self.source_location_id.id,
                    'location_dest_id': self.destination_location_id.id,
                }
                stock_moves.append((0, 0, stock_move_vals))

        if stock_moves:
            # Get internal picking type
            internal_picking_type = self.warehouse_id.int_type_id if self.warehouse_id else self.env.ref('stock.picking_type_internal', raise_if_not_found=False)
            if not internal_picking_type:
                raise ValidationError("No internal picking type found for the warehouse.")

            stock_picking = self.env['stock.picking'].create({
                'location_id': self.source_location_id.id,
                'location_dest_id': self.destination_location_id.id,
                'picking_type_id': internal_picking_type.id,
                'move_ids_without_package': stock_moves,
                'origin': self.name,
            })
            
            stock_picking.action_confirm()
            stock_picking.action_assign()
            self.picking_id = stock_picking.id

    def _create_accounting_entry(self):
        """Create accounting journal entry for total cost transfer"""
        if not self.source_location_id.account_id or not self.destination_location_id.account_id:
            raise ValidationError("Both source and destination locations must have chart of accounts configured.")
        
        # Get inventory valuation journal from settings
        journal_id = int(self.env['ir.config_parameter'].sudo().get_param('production_custom_module.inventory_valuation_journal_id', False))
        journal = self.env['account.journal'].browse(journal_id)
        if not journal:
            raise ValidationError("No inventory valuation journal configured in settings.")
        
        move_vals = {
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'ref': f"FGRN - {self.name}",
            'company_id': self.company_id.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.source_location_id.account_id.id,
                    'credit': self.total_cost,
                    'name': f"FGRN from {self.source_location_id.name} for {self.name}",
                }),
                (0, 0, {
                    'account_id': self.destination_location_id.account_id.id,
                    'debit': self.total_cost,
                    'name': f"FGRN to {self.destination_location_id.name} for {self.name}",
                }),
            ],
        }
        journal=self.env['account.move'].create(move_vals)
        journal.action_post()
        self.journal_id=journal.id

    def _update_product_costs(self):
        """Update product costs based on divided_by method"""
        if not self.bill_of_material_lines:
            return
        
        total_quantity = sum(line.quantity for line in self.bill_of_material_lines if line.quantity > 0)
        
        for line in self.bill_of_material_lines:
            if line.quantity <= 0:
                continue
                
            
                # Divide cost based on quantity proportion
            if total_quantity > 0:
                allocated_cost = (line.quantity / total_quantity) * self.total_cost
                new_product_cost = allocated_cost / line.quantity
            else:
                new_product_cost = line.cost
                    
           
            # Update product standard price
            if new_product_cost != line.product_id.standard_price:
                line.product_id.write({'standard_price': new_product_cost})
                _logger.info(f"Updated {line.product_id.name} cost from {line.product_id.standard_price} to {new_product_cost} based on FGRN {self.name}")

    def view_stock_picking(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Picking',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'target': 'current',
        }


    def view_account_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('id', '=', self.journal_id.id)],
            'target': 'current',  # or 'new' for a popup
        }     
    
    


class FGRNBOMLine(models.Model):
    _name = 'fgrn.bom.line'
    _description = 'FGRN Bill of Material Line'

    fgrn_id = fields.Many2one('fgrn.return', string="FGRN", ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Product", required=True)
    quantity = fields.Float(string="Quantity", required=True, default=0.0)
    cost = fields.Float(string="Cost",compute="_onchange_product_id" ,readonly=True)
    store_issue_id = fields.Many2one('store.request', string="Store Issue")
    original_store_line_id = fields.Many2one('store.request.line', string="Original Store Line", readonly=True)
    available_qty = fields.Float(
        string="Available Quantity",
        compute="_compute_available_qty",
        store=False,
    )

    @api.depends('product_id', 'fgrn_id.source_location_id')
    def _compute_available_qty(self):
        for line in self:
            if line.product_id and line.fgrn_id.source_location_id:
                quants = self.env['stock.quant'].search([
                    ('location_id', '=', line.fgrn_id.source_location_id.id),
                    ('product_id', '=', line.product_id.id)
                ])
                line.available_qty = sum(quants.mapped('available_quantity'))
            else:
                line.available_qty = 0.0

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_("Quantity must be greater than 0"))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for record in self:
            record.cost = 0.0  # default
            if record.fgrn_id and record.product_id:
                # Search in all related store issue voucher lines
                all_lines = record.fgrn_id.store_issue_ids.mapped('voucher_lines')
                # Find matching line(s) with same product
                matching_line = all_lines.filtered(lambda l: l.product_id == record.product_id)
                if matching_line:
                    record.cost = matching_line[0].cost

  