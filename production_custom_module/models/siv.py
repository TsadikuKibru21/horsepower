from odoo import models, fields, api,_
from odoo.exceptions import ValidationError, UserError
import logging


class storeRequest(models.Model):
    _name = 'store.request'
    _description = 'store Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="Reference", copy=False, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    # effective_date = fields.Date(string="Effective Date", default=fields.Date.today())
    # store_request = fields.Char(string="Store Request")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", domain="[('company_id', 'in', allowed_company_ids)]",track_visibility="always")
    location_id = fields.Many2one('stock.location', string="Location", domain="[('usage', '=', 'internal'), ('warehouse_id', '=', warehouse_id)]",track_visibility="always")
    destination_location_id = fields.Many2one('stock.location', string="Destination Location", domain="[('usage', 'in', ['customer', 'internal'])]",track_visibility="always")
    transfer_type = fields.Selection([('out', 'Out'), ('internal', 'Internal')], string="Transfer Type", default='internal',track_visibility="always")
    submit_user_id = fields.Many2one('res.users', string="Submitted By", readonly=True,track_visibility="always")
    validate_user_id = fields.Many2one('res.users', string="Validated By", readonly=True,track_visibility="always")
    state = fields.Selection([('draft', 'Draft'), ('submitted', 'Submitted'), ('validated', 'Validated'),('accepted', 'Accepted')], default='draft', track_visibility='always')
    voucher_lines = fields.One2many('store.request.line', 'request_id', string="Voucher Lines")
    len_picking_id=fields.Integer(compute='_compute_picking')
    # approved_date = fields.Date(string="Approved Date")
    submitted_date = fields.Date(string="Submitted Date", readonly=True)
    validated_date = fields.Date(string="Validated Date", readonly=True)
    picking_id = fields.Many2one('stock.picking', string="Transfer", readonly=True)
    journal_id = fields.Many2one('account.move', string="Journal", readonly=True)
    len_journal_id=fields.Integer(compute='_compute_journal')
    remaining_cost = fields.Float(string="Remaining Cost", compute='_compute_remaining_cost', store=True)


    active=fields.Boolean(default=True)
    
    @api.depends('voucher_lines', 'voucher_lines.cost', 'voucher_lines.quantity')
    def _compute_remaining_cost(self):
        for record in self:
            total_cost = sum(line.quantity * line.cost for line in record.voucher_lines)
            used_cost = 0.0
            # Find all FGRN BOM lines linked to this store request
            bom_lines = self.env['fgrn.bom.line'].search([
                ('fgrn_id.store_issue_ids', 'in', [record.id]),
                ('fgrn_id.state', '=', 'validated')
            ])
            for bom_line in bom_lines:
                used_cost += bom_line.quantity * bom_line.cost
            record.remaining_cost = total_cost - used_cost
    @api.model
    def create(self, vals):
        if 'name' not in vals or vals['name'] == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('store.request')
        return super(storeRequest, self).create(vals)
    def action_submit(self):
        self.write({'state': 'submitted', 'submit_user_id': self.env.user,'submitted_date': fields.Date.today()})

    def action_validate(self):
        self.write({'state': 'validated', 'validate_user_id': self.env.user, 'validated_date': fields.Date.today()})
        self.action_create_transfer()
    def action_create_transfer(self):
        stock_moves = []
        total_cost = 0.0
        for line in self.voucher_lines:
            stock_move_vals = {
                'name': self.name,
                'product_id': line.product_id.id,
                'product_uom': line.product_id.uom_id.id,
                'product_uom_qty': line.quantity,
                'origin': self.name,
                'location_id': self.location_id.id if self.location_id else False,
                'location_dest_id': self.destination_location_id.id if self.destination_location_id else False,
            }
            stock_moves.append((0, 0, stock_move_vals))
            total_cost += line.total_cost

        if stock_moves:
            # Fetch the internal picking type from the warehouse
            internal_picking_type = self.warehouse_id.int_type_id if self.warehouse_id else self.env.ref('stock.picking_type_internal', raise_if_not_found=False)
            
            if not internal_picking_type:
                raise ValidationError("No internal picking type found for the warehouse or in the system.")

            stock_picking = self.env['stock.picking'].create({
                'location_id': self.location_id.id if self.location_id else False,
                'location_dest_id': self.destination_location_id.id if self.destination_location_id else False,
                'picking_type_id': internal_picking_type.id,
                'move_ids_without_package': stock_moves,
                'origin': self.name,
            })
            
            stock_picking.action_confirm()
            stock_picking.action_assign()
            self.picking_id = stock_picking.id

            # Create accounting journal entry
            if total_cost > 0 and self.location_id.account_id and self.destination_location_id.account_id:
                journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
                if not journal:
                    raise ValidationError("No general journal found for the company.")
                journal_id = int(self.env['ir.config_parameter'].sudo().get_param('production_custom_module.inventory_valuation_journal_id', False))
                journal = self.env['account.journal'].browse(journal_id)
                if not journal:
                    raise ValidationError("No inventory valuation journal configured in settings.")
                
                move_vals = {
                    'journal_id': journal.id,
                    'date': fields.Date.today(),
                    'ref': f"Stock Transfer {self.name}",
                    'company_id': self.company_id.id,
                    'line_ids': [
                        (0, 0, {
                            'account_id': self.location_id.account_id.id,
                            'credit': total_cost,
                            'name': f"Stock transfer from {self.location_id.name} for {self.name}",
                        }),
                        (0, 0, {
                            'account_id': self.destination_location_id.account_id.id,
                            'debit': total_cost,
                            'name': f"Stock transfer to {self.destination_location_id.name} for {self.name}",
                        }),
                    ],
                }
                jounal=self.env['account.move'].create(move_vals).action_post()
                self.journal_id=jounal.id

    def _compute_picking(self):
        for record in self:
            data=self.env['stock.picking'].search([
                ('id','=',record.picking_id.id)
            ],limit=1)
            record.len_picking_id=len(data)
    def _compute_journal(self):
        for record in self:
            data=self.env['account.move'].search([
                ('id','=',record.journal_id.id)
            ],limit=1)
            record.len_journal_id=len(data)

    def view_stock_picking(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Picking',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('id', '=', self.picking_id.id)],
            'target': 'current',  # or 'new' for a popup
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
    
    
   





class storeRequestLine(models.Model):
    _name = 'store.request.line'
    _description = 'store Request Line'

    request_id = fields.Many2one('store.request', string="Request")
    product_id = fields.Many2one('product.product', string="Product", required=True)
    quantity = fields.Float(string="Quantity", default=0.0)
    cost = fields.Float(string="Cost")
    available_qty = fields.Float(
        string="Available Quantity",
        compute="_compute_available_qty",
        store=False,
    )
    total_cost=fields.Float(string="Total Cost",compute="compute_total_cost")

    @api.depends('product_id', 'quantity','cost')
    def compute_total_cost(self):

        for record in self:
            record.total_cost=record.quantity * record.cost

    @api.depends('product_id', 'request_id.location_id')
    def _compute_available_qty(self):
        for line in self:
            if line.product_id and line.request_id.location_id:
                qty = self.env['stock.quant'].search([
                    ('location_id', '=', line.request_id.location_id.id),
                    ('product_id', '=', line.product_id.id)
                ]).mapped('available_quantity')
                line.available_qty = sum(qty)
            else:
                line.available_qty = 0.0

    @api.constrains('quantity')
    def check_quantity(self):
        for record in self:
            if record.quantity <=0:
                raise ValidationError("Quantity Should be Greater Than 0")


