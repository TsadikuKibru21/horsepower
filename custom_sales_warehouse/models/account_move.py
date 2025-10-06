from odoo import api, fields, models



class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'
    is_closing_required = fields.Boolean(
        string='Closing Required',
    )
    
    @api.model
    def _check_misconfigured_tax_groups(self, company, countries):
        """Extend to check misconfigured tax groups only if closing is required."""
        # Build domain with the new condition for is_closing_required
        domain = [
            *self.env['account.tax']._check_company_domain(company),
            ('country_id', 'in', countries.ids),
            ('tax_group_id.is_closing_required', '=', True),  # Only check groups that require closing
            '|',
            ('tax_group_id.tax_payable_account_id', '=', False),
            ('tax_group_id.tax_receivable_account_id', '=', False),
        ]
        # Call super with the extended domain (note: super uses its own domain, but we override fully here for clarity)
        # Since we're overriding, we use the new domain directly
        return bool(self.env['account.tax'].search(domain, limit=1))
class AccountMoveLine(models.Model):
    _inherit="account.move.line"

    order_sequence=fields.Char(string="NO")
    default_code = fields.Many2one('product.item.code', string="Item Code",ondelete="cascade")
    
   
            
    @api.model
    def create(self, vals):
        if 'product_id' in vals and vals.get('product_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            if product.item_code_id:
                vals['default_code'] = product.item_code_id.id
        if 'default_code' in vals and vals.get('default_code'):
            code = self.env['product.item.code'].browse(vals['default_code'])
            if not code.exists():
                vals['default_code'] = False
        return super(AccountMoveLine, self).create(vals)

    @api.onchange('default_code')
    def _onchange_default_code(self):
        if self.default_code:
            self.product_id = self.default_code.product_id
        else:
            self.product_id = False
            self.default_code = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.default_code = self.product_id.item_code_id
        else:
            self.default_code = False
