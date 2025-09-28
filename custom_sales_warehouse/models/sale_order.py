from odoo import models, fields, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    sales_from_id = fields.Many2many('sales.from', string='Sales From')
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
    quotation_status = fields.Char(string="Quotation Status")
   
    state = fields.Selection([
        
        ('draft', 'New'),
        ('to_approve', 'Submitted'),
        ('approved', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', copy=False, tracking=True, default='draft')

    def action_print_quotation_order(self):
        return self.env.ref('sale.action_report_saleorder').report_action(self)

    def action_print_pro_forma(self):
        return self.env.ref('sale.action_report_pro_forma_invoice').report_action(self)

    def action_submit_for_approval(self):
        for order in self:
            order.state = 'to_approve'

    def action_approve(self):
        for order in self:
            
            result = order._reserve_stock()
            if result:
                return result
            order.state = 'approved'
        return True


    @api.depends('user_id')
    def _compute_team(self):
        for order in self:
            team = self.env['crm.team'].search([
                ('member_ids', 'in', [self.env.uid])
            ], limit=1)
            order.team = team.team if team else False

    def action_cancel(self):
        """Cancel the sale order and unreserve stock."""
        for order in self:
            # Unreserve stock before canceling
            order._unreserve_stock()
            _logger.info("Unreserved stock for order %s", order.name)
        # Call the parent action_cancel to handle standard cancellation
        res = super(SaleOrder, self).action_cancel()
        _logger.info("Completed action_cancel for orders: %s", self.mapped('name'))
        return res
    
    def _unreserve_stock(self):
        """Unreserve stock for sale order lines."""
        for order in self:
            warehouse = order.warehouse_id
            if not warehouse:
                _logger.warning("No warehouse defined for sale order %s, skipping unreservation", order.name)
                continue

            for line in order.order_line:
                product = line.product_id
                qty_to_unreserve = line.product_uom_qty
                _logger.info("Attempting to unreserve %s units of product %s for order %s",
                             qty_to_unreserve, product.name, order.name)

                # Find reserved stock in the warehouse
                stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', warehouse.lot_stock_id.id),
                    # ('reserved_quantity', '>', 0),
                ], limit=1)

                if stock_quant and stock_quant.reserved_quantity >= qty_to_unreserve:
                    # Unreserve stock by updating quant with negative quantity
                    stock_quant._update_reserved_quantity(
                        product_id=product,
                        location_id=warehouse.lot_stock_id,
                        quantity=-qty_to_unreserve,
                    
                    )
                    _logger.info("Unreserved %s units of product %s in warehouse %s for order %s",
                                 qty_to_unreserve, product.name, warehouse.name, order.name)
                else:
                    _logger.warning("No reserved stock found for product %s in warehouse %s for order %s",
                                    product.name, warehouse.name, order.name)

    def _reserve_stock(self):
        """Reserve stock for sale order lines when reaching draft state."""
        for order in self:
            _logger.info("Starting stock reservation for Sale Order: %s", order.name)
            
            warehouse = order.warehouse_id
            if not warehouse:
                _logger.error("No warehouse defined for Sale Order: %s", order.name)
                raise UserError(f"No warehouse defined for sale order {order.name}")
            
            _logger.info("Using warehouse: %s", warehouse.name)

            insufficient_products = []
            for line in order.order_line:
                product = line.product_id
                qty_needed = line.product_uom_qty
                _logger.info("Checking line: Product %s, Quantity needed: %s", product.name, qty_needed)

                # Search available stock
                stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', warehouse.lot_stock_id.id),
                    ('quantity', '>', 0),
                ], limit=1)

                if stock_quant:
                    _logger.info("Found stock quant: Product %s, Total Qty: %s, Reserved: %s, Available: %s",
                                product.name, stock_quant.quantity, stock_quant.reserved_quantity,
                                stock_quant.quantity - stock_quant.reserved_quantity)
                else:
                    _logger.warning("No stock quant found for product %s in warehouse %s", product.name, warehouse.name)

                available_qty = stock_quant.quantity - stock_quant.reserved_quantity if stock_quant else 0.0

                if qty_needed > available_qty:
                    _logger.warning("Insufficient stock for product %s: Needed %s, Available %s",
                                    product.name, qty_needed, available_qty)
                    insufficient_products.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'qty_needed': qty_needed,
                        'qty_available': available_qty,
                        'order_id': order.id,
                    })
                else:
                    _logger.info("Sufficient stock available. Reserving %s units of product %s",
                                qty_needed, product.name)
                    stock_quant._update_reserved_quantity(
                        product_id=product,
                        location_id=warehouse.lot_stock_id,
                        quantity=qty_needed
                    )
                    _logger.info("Successfully reserved %s units of %s in warehouse %s for order %s",
                                qty_needed, product.name, warehouse.name, order.name)

            if insufficient_products:
                _logger.warning("Some products have insufficient stock for order %s", order.name)
                message = "The following products have insufficient stock:\n"
                for item in insufficient_products:
                    message += f"- {item['product_name']}: Needed {item['qty_needed']}, Available {item['qty_available']}\n"
                    _logger.debug("Insufficient: %s - Needed: %s, Available: %s",
                                item['product_name'], item['qty_needed'], item['qty_available'])

                message += "Do you want to reserve the available quantity?"

                _logger.info("Creating wizard for insufficient stock notification")
                wizard = self.env['sale.order.stock.wizard'].create({
                    'message': message,
                    'order_id': order.id,
                    'product_data': [(0, 0, {
                        'product_id': item['product_id'],
                        'qty_needed': item['qty_needed'],
                        'qty_available': item['qty_available'],
                    }) for item in insufficient_products]
                })

                _logger.info("Wizard created: %s, returning form view for user confirmation", wizard.id)
                # return {
                #     'type': 'ir.actions.act_window',
                #     'res_model': 'sale.order.stock.wizard',
                #     'view_mode': 'form',
                #     'res_id': wizard.id,
                #     'target': 'new',
                # }
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Insufficient Stock Warning',
                    'res_model': 'sale.order.stock.wizard',
                    'view_mode': 'form',
                    'res_id': wizard.id,
                    'target': 'new',
            }

            
            _logger.info("Stock reservation completed for order %s", order.name)
        return False
                    # Optionally raise an error or notify user
                    # raise UserError(f"Insufficient stock for product {product.name} in warehouse {warehouse.name}")

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

                _logger.info("Checking stock for product: %s, Quantity: %s in order: %s", product.name, qty_needed, order.name)

                # Step 1: Check stock in current warehouse (already reserved in draft state)
                stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('location_id', '=', warehouse.lot_stock_id.id),
                    # ('reserved_quantity', '>', 0)
                ], limit=1)

                if stock_quant and stock_quant.reserved_quantity >= qty_needed:
                    _logger.info("Using reserved stock for product: %s in warehouse %s for order %s",
                                 product.name, warehouse.name, order.name)
                    qty_remaining = 0
                else:
                    # Check unreserved stock if reservation was partial or failed
                    stock_quant = self.env['stock.quant'].search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', warehouse.lot_stock_id.id),
                        # ('quantity', '>', 0)
                    ], limit=1)
                    if stock_quant and stock_quant.quantity > 0:
                        qty_available = min(stock_quant.quantity - stock_quant.reserved_quantity, qty_needed)
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

                    if other_quant and other_quant.quantity > 0:
                        qty_to_transfer = min(other_quant.quantity, qty_remaining)

                        # Determine the source warehouse from the quant's location
                        source_warehouse = self.env['stock.warehouse'].search([
                            ('lot_stock_id', '=', other_quant.location_id.id)
                        ], limit=1)
                        if not source_warehouse:
                            source_warehouse = other_quant.location_id.get_warehouse()

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
                        'product_id': product.id,
                        'quantity': qty_remaining,
                    }))

            # Create a single purchase request for the order if needed
            if purchase_request_lines:
                _logger.info("Creating purchase request for order: %s", order.name)
                purchase_request = self.env['purchase.request'].create({
                    'effective_date': fields.Date.today(),
                    'request_lines': purchase_request_lines,
                    'sale_order': order.id,
                })
                _logger.info("Created purchase request %s for order: %s", purchase_request.name, order.name)

        _logger.info("Completed action_confirm for orders: %s", self.mapped('name'))
        return res


class SaleOrderStockWizard(models.TransientModel):
    _name = 'sale.order.stock.wizard'
    _description = 'Sale Order Stock Reservation Wizard'

    message = fields.Text(string='Message', readonly=True)
    order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    product_data = fields.One2many('sale.order.stock.wizard.line', 'wizard_id', string='Product Data')

    def action_reserve_remaining(self):
        """Reserve the available stock for products in the wizard."""
        for wizard in self:
            order = wizard.order_id
            warehouse = order.warehouse_id
            for line in wizard.product_data:
                product = line.product_id
                qty_to_reserve = min(line.qty_needed, line.qty_available)
                if qty_to_reserve > 0:
                    stock_quant = self.env['stock.quant'].search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', warehouse.lot_stock_id.id),
                        # ('quantity', '>', 0),
                        # ('reserved_quantity', '<', 'quantity'),
                    ], limit=1)
                    if stock_quant:
                        stock_quant._update_reserved_quantity(
                            product_id=product,
                            location_id=warehouse.lot_stock_id,
                            quantity=qty_to_reserve,
                            # lot_id=False,
                            # package_id=False,
                            # owner_id=False,
                            # strict=True
                        )
                        _logger.info("Reserved %s units of product %s in warehouse %s for order %s",
                                     qty_to_reserve, product.name, warehouse.name, order.name)
            # Proceed to draft state after reserving available stock
            order.state = 'approved'
        return {'type': 'ir.actions.act_window_close'}


class SaleOrderStockWizardLine(models.TransientModel):
    _name = 'sale.order.stock.wizard.line'
    _description = 'Sale Order Stock Wizard Line'

    wizard_id = fields.Many2one('sale.order.stock.wizard', string='Wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    qty_needed = fields.Float(string='Quantity Needed', readonly=True)
    qty_available = fields.Float(string='Quantity Available', readonly=True)