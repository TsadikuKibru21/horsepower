from odoo import api, fields, models

from odoo.exceptions import UserError, ValidationError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.name

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends('name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.name
            
            
    item_code_id = fields.Many2one(
        'product.item.code',
        string="Item Code",
        ondelete='cascade'
    )

    @api.depends('item_code_id.default_code')
    def _compute_default_code(self):
        for rec in self:
            rec.default_code = rec.item_code_id.default_code if rec.item_code_id else False

    def _inverse_default_code(self):
        for rec in self:
            if rec.default_code:
                if rec.item_code_id:
                    rec.item_code_id.default_code = rec.default_code
                else:
                    rec.item_code_id = self.env['product.item.code'].create({
                        'default_code': rec.default_code,
                        'product_id': rec.id
                    })
            else:
                if rec.item_code_id:
                    rec.item_code_id.unlink()
                    rec.item_code_id = False

    def _check_item_code_unique(self):
        for rec in self:
            if rec.default_code:
                dups = self.env['product.product'].search_count([
                    ('id', '!=', rec.id),
                    ('default_code', '=', rec.default_code),
                ])
                if dups > 0:
                    raise ValidationError("Duplicate Item Code.")

    @api.model
    def create(self, vals):
        res = super(ProductProduct, self).create(vals)
        res._inverse_default_code()
        res._check_item_code_unique()
        return res

    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        self._inverse_default_code()
        self._check_item_code_unique()
        return res