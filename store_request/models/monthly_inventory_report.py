from odoo import models,fields,api 


class MonthlyReport(models.Model):
    _name="monthly.inventory.report"
    _description="Monthly Inventory Report"

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    operation_type= fields.Many2many("stock.picking.type",string="Operation Type", default=lambda self: self._get_all_stock_picking_types())
    
    stock_pickings= fields.Many2many("stock.picking",string="Stock Pickings",compute="_compute_stock_pickings")


    
    def _get_all_stock_picking_types(self):
            stock_picking_types = self.env["stock.picking.type"].search([])
            return stock_picking_types
            
    @api.depends("start_date","end_date")
    def _compute_stock_pickings(self):
        for record in self:
            domain = [
                ("date","<=",record.end_date),
                ("date",">=",record.start_date),
                ("state","in",["done","assigned"])
            ]
            if record.operation_type:
                domain.append(("picking_type_id","in",record.operation_type.ids))
            stock_pickings = self.env["stock.picking"].search(domain)
            record.stock_pickings = stock_pickings

    
