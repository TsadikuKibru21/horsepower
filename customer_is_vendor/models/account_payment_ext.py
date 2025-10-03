from odoo import api, models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        domain = []
        if self.partner_type == 'customer':
            domain = [('is_customer', '>', 0)]
        elif self.partner_type == 'supplier':
            domain = [('is_vendor', '>', 0)]
        return {
            'domain': {'partner_id': domain}
        }
