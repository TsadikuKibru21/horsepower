from odoo import models, fields, api,_
from odoo.exceptions import UserError,ValidationError
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    team = fields.Selection(
        selection=[
            ('direct_sales', 'Direct Sales'),
            ('estimated_tender', 'Estimated Tender'),
        ],
        string="Team",
        compute='_compute_team',
        store=True,
        readonly=False
    )
    quotation_status = fields.Selection([
        ('a','A'),
        ('b','B'),
        ('c','C'),
        ('d','D'),
        ],string="Quotation Status")
   
    state = fields.Selection([
        
        ('draft', 'New'),
        ('to_approve', 'Submitted'),
        ('approved', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', copy=False, tracking=True, default='draft')
    release_from_confirm=fields.Boolean()
    is_reserved=fields.Boolean()
    
    have_waranty=fields.Boolean(string="Have Waranty")
    
    waranty_expiration_date = fields.Date(string="Expiration Date")

    def action_print_quotation_order(self):
        return self.env.ref('sale.action_report_saleorder').report_action(self)

    def action_print_pro_forma(self):
        return self.env.ref('sale.action_report_pro_forma_invoice').report_action(self)
    
    quotation_print_limit = fields.Float(
        string="Quotation Print Limit",
        compute="_compute_quotation_print_limit",
        store=False
    )

    def _compute_quotation_print_limit(self):
        """Get limit value from system parameter."""
        limit_value = float(self.env['ir.config_parameter'].sudo().get_param(
            'custom_sales_warehouse.quotation_print_limit', 0
        ))
        for rec in self:
            rec.quotation_print_limit = limit_value

    def action_submit_for_approval(self):
        for order in self:
            order.state = 'to_approve'

    def action_approve(self):
        for order in self:
            
            
            order.state = 'approved'


    @api.depends('user_id')
    def _compute_team(self):
        for order in self:
            team = self.env['crm.team'].search([
                ('member_ids', 'in', [self.env.uid])
            ], limit=1)
            order.team = team.team if team else False

  
   

    

    def action_confirm(self):
        valid_states = ['draft', 'sent', 'approved']
        invalid_orders = self.filtered(lambda o: o.state not in valid_states)
        if invalid_orders:
            raise UserError(
                f"The following orders are not in a state requiring confirmation: {', '.join(invalid_orders.mapped('name'))}"
            )

        # Temporarily set state to 'draft' for orders in 'approved' to bypass Odoo's default check
        approved_orders = self.filtered(lambda o: o.state == 'approved')
        if approved_orders:
            approved_orders.write({'state': 'draft'})
        _logger.info("Starting action_confirm for orders: %s", self.mapped('name'))
        res = super(SaleOrder, self).action_confirm()
        _logger.info("Super action_confirm called for orders: %s", self.mapped('name'))

        for order in self:
            order.release_from_confirm =True
            order.action_release_products()
            use_custom_flow = False
            purchase_request_lines = []
            
            # Check if any product uses custom stock flow
            for line in order.order_line:
                routes = line.product_id.route_ids
                if routes.filtered(lambda r: r.is_custom_stock_flow):
                    use_custom_flow = True
                    break

            if not use_custom_flow:
                _logger.info("No custom stock flow for order: %s, proceeding with default flow", order.name)
                continue

            _logger.info("Processing custom stock flow for order: %s, Warehouse: %s", order.name, order.warehouse_id.name)

            for line in order.order_line:
                product = line.product_id
                qty_needed = line.product_uom_qty
                qty_remaining = qty_needed
                warehouse = order.warehouse_id
                partner_id=line.sales_from_id.partner_id

              

               
                stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', warehouse.lot_stock_id.id),
                    # ('quantity', '>', 0)
                ], limit=1)
                if stock_quant and stock_quant.inventory_quantity_auto_apply > 0:
                    qty_available = min(stock_quant.inventory_quantity_auto_apply ,qty_needed)
                    _logger.info("Found %s unreserved units in warehouse %s for product: %s",
                                    qty_available, warehouse.name, product.name)
                    qty_remaining -= qty_available

                # Step 2: Check stock in other warehouses if needed
                if qty_remaining > 0:
                    _logger.info("Checking other warehouses for product: %s, Remaining: %s", product.name, qty_remaining)
                    other_quant = self.env['stock.quant'].search([
                        ('product_id', '=', product.id),
                        ('location_id', '!=', warehouse.lot_stock_id.id),
                        ('location_id.usage', '=', 'internal'),
                        # ('quantity', '>', 0)
                    ], limit=1)

                    if other_quant and other_quant.inventory_quantity_auto_apply > 0:
                        qty_to_transfer = min(other_quant.inventory_quantity_auto_apply, qty_remaining)

                        # Determine the source warehouse from the quant's location
                        source_warehouse = self.env['stock.warehouse'].search([
                            ('lot_stock_id', '=', other_quant.location_id.id)
                        ], limit=1)
                        if not source_warehouse:
                            source_warehouse = order.warehouse_id

                        # Use the internal picking type from the source warehouse
                        picking_type = self.env['stock.picking.type'].search([
                            ('code', '=', 'internal'),
                            ('warehouse_id', '=', source_warehouse.id)
                        ], limit=1)
                        if not picking_type:
                            raise UserError(f"No internal picking type found for source warehouse {source_warehouse.name}")

                        internal_picking = self.env['stock.picking'].create({
                            'picking_type_id': picking_type.id,
                            'location_id': other_quant.location_id.id,
                            'location_dest_id': warehouse.lot_stock_id.id,
                            'origin': order.name,
                            'move_ids': [(0, 0, {
                                'name': f'Internal Transfer for {order.name}',
                                'product_id': product.id,
                                'product_uom_qty': qty_to_transfer,
                                'quantity': qty_to_transfer,
                                'product_uom': product.uom_id.id,
                                'location_id': other_quant.location_id.id,
                                'location_dest_id': warehouse.lot_stock_id.id,
                                'sale_line_id': line.id,
                            })]
                        })
                        internal_picking.action_assign()
                        _logger.info("Created internal picking %s for product: %s from %s to %s using picking type %s",
                                     internal_picking.name, product.name, other_quant.location_id.name,
                                     warehouse.lot_stock_id.name, picking_type.name)
                        qty_remaining -= qty_to_transfer

                # Step 3: Add to purchase request lines if quantity remains
                if qty_remaining > 0:
                    _logger.info("Adding purchase request line for product: %s, Remaining: %s", product.name, qty_remaining)
                    purchase_request_lines.append((0, 0, {
                        'order_sequence':line.order_sequence,
                        'product_id': product.id,
                        'quantity': qty_remaining,
                        'vendor':partner_id.id
                    }))

            # Create a single purchase request for the order if needed
            if purchase_request_lines:
                _logger.info("Creating purchase request for order: %s", order.name)
                purchase_request = self.env['purchase.request'].create({
                    'effective_date': fields.Date.today(),
                    'request_lines': purchase_request_lines,
                    'sale_order': order.id,
                    'requester_id':self.env.user.id,
                })
                _logger.info("Created purchase request %s for order: %s", purchase_request.name, order.name)

        _logger.info("Completed action_confirm for orders: %s", self.mapped('name'))
        return res
    
    
    
    
    
    def _get_sale_location(self):
        """Helper: get location_id from sale order's warehouse."""
        self.ensure_one()
        warehouse = self.warehouse_id
        if not warehouse or not warehouse.lot_stock_id:
            raise UserError(_("No stock location found for warehouse %s.") % warehouse.display_name)
        return warehouse.lot_stock_id.id

    def action_reserve_products(self):
        """Reserve quantities directly in stock.quant."""
        for order in self:
       

            location_id = order._get_sale_location()

            for line in order.order_line:
                product = line.product_id
                qty = line.product_uom_qty

                quant = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', location_id),
                ], limit=1)

                if quant:
                    quant.reserved_quantity += qty
                else:
                    self.env['stock.quant'].create({
                        'product_id': product.id,
                        'location_id': location_id,
                        'reserved_quantity': qty,
                    })
            order.is_reserved=True


    def action_release_products(self):
        """Release reserved quantities from stock.quant."""
        for order in self:
        

            location_id = order._get_sale_location()

            for line in order.order_line:
                product = line.product_id
                qty = line.product_uom_qty

                quant = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', location_id),
                ], limit=1)

                if quant:
                    new_reserved = quant.reserved_quantity - qty
                    quant.reserved_quantity = new_reserved if new_reserved > 0 else 0.0
            if not order.release_from_confirm:
                order.quotation_status="b"
            order.is_reserved=False

