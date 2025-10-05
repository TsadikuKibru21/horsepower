from odoo import models, fields,api,_
from odoo.exceptions import UserError, ValidationError
class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    warehouse_manager_ids = fields.Many2many(
        comodel_name='res.users',
        relation='stock_warehouse_manager_rel',
        column1='warehouse_id',
        column2='user_id',
        string='Warehouse Managers',
        help='Users who can view and validate inventory operations for this warehouse.'
    )

class StockPicking(models.Model):
    _inherit = "stock.picking"

    show_validate_button = fields.Boolean(compute="_compute_show_validate_button")

    @api.depends('picking_type_id.warehouse_id.warehouse_manager_ids')
    def _compute_show_validate_button(self):
        for picking in self:
            warehouse = picking.picking_type_id.warehouse_id
            managers = warehouse.warehouse_manager_ids
            picking.show_validate_button = self.env.uid in managers.ids if managers else False
            
            
    def button_validate(self):
        for picking in self:
            if picking.show_validate_button != True:
                raise ValidationError(_("You are not allowed to validate the Operation."))

        return super(StockPicking, self).button_validate()
