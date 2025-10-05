from odoo import api, fields, models,_

from odoo.exceptions import UserError, ValidationError,AccessError
class ResPartner(models.Model):
    _inherit = 'res.partner'
    is_contact_manager_user = fields.Boolean(
        string='Is Contact Manager User',
        compute='_compute_is_contact_manager_user',
        store=False
    )
    @api.depends('name')
    def _compute_is_contact_manager_user(self):
        for partner in self:
            partner.is_contact_manager_user = self.env.user.has_group('custom_sales_warehouse.group_contact_manager')
    is_contact_manager_user
    def write(self, vals):
      
        if self.env.user.id != 1 and not self.env.user.has_group("custom_sales_warehouse.group_contact_manager"):
                raise AccessError(_("You are not allowed to Create Contact."))
        res = super().write(vals)
       
        return res

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.depends('name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.name
            
        
    def create(self, vals):
        if self.env.user.id != 1 and not self.env.user.has_group("custom_sales_warehouse.group_product_manager"):
            raise AccessError(_("You are not allowed to create products."))
        return super().create(vals)

    def write(self, vals):
        allowed_fields = {
            "standard_price", 
            "last_purchase_price", 
            "currency_id", 
            "seller_ids"
        }
        if self.env.user.id != 1 and not self.env.user.has_group("custom_sales_warehouse.group_product_manager"):
            if not set(vals.keys()).issubset(allowed_fields):
                raise AccessError(_("You are not allowed to modify products."))
        return super().write(vals)

    def unlink(self):
        if self.env.user.id != 1 and not self.env.user.has_group("custom_sales_warehouse.group_product_manager"):
            raise AccessError(_("You are not allowed to delete products."))
        return super().unlink()


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
        if self.env.user.id != 1 and not self.env.user.has_group("custom_sales_warehouse.group_product_manager"):
            raise AccessError(_("You are not allowed to create product variants."))
        res = super().create(vals)
        res._inverse_default_code()
        res._check_item_code_unique()
        return res

    def write(self, vals):
        allowed_fields = {
            "standard_price", 
            "last_purchase_price", 
            "currency_id", 
            "seller_ids"
        }
        if self.env.user.id != 1 and not self.env.user.has_group("custom_sales_warehouse.group_product_manager"):
            if not set(vals.keys()).issubset(allowed_fields):
                raise AccessError(_("You are not allowed to modify product."))
        res = super().write(vals)
        self._inverse_default_code()
        self._check_item_code_unique()
        return res

    
    def unlink(self):
        if self.env.user.id != 1 and not self.env.user.has_group("custom_sales_warehouse.group_product_manager"):
            raise AccessError(_("You are not allowed to delete products."))
        return super().unlink()

    

