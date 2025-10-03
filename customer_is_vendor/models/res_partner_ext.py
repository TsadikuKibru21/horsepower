# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
class PartnerTin(models.Model):
    _name = 'partner.tin'
    _description = 'Partner TIN'
    _rec_name = 'tin_number'

    tin_number = fields.Char(string="TIN", required=True)
    partner_id = fields.Many2one('res.partner', string="Partner",ondelete="cascade")

    
class ResPartner(models.Model):
    _inherit = 'res.partner'
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)

    # is_customer = fields.Boolean(string='Is A Customer', defualt=False, tracking=True)
    is_vendor = fields.Boolean(string='Is A Vendor')
    is_customer = fields.Boolean(string='Is A Customer')
    # salesperson_id = fields.Many2one('res.users', string='Agent')
    # is_contact_manager_user = fields.Boolean(
    #     string='Is Contact Manager User',
    #     compute='_compute_is_contact_manager_user',
    #     store=False
    # )
    # @api.depends('name')
    # def _compute_is_contact_manager_user(self):
    #     for partner in self:
    #         partner.is_contact_manager_user = self.env.user.has_group('customer_is_vendor.group_contact_manager')
    
    tin_id = fields.Many2one(
        'partner.tin',
        string="TIN",
        ondelete='cascade'  # ✅ this ensures delete cascade
    )

    @api.depends('tin_id.tin_number')
    def _compute_vat(self):
        for rec in self:
            rec.vat = rec.tin_id.tin_number if rec.tin_id else False

    def _inverse_vat(self):
        for rec in self:
            if rec.vat:
                if rec.tin_id:
                    rec.tin_id.tin_number = rec.vat
                else:
                    rec.tin_id = self.env['partner.tin'].create({
                        'tin_number': rec.vat,
                        'partner_id': rec.id
                    })
            else:
                if rec.tin_id:
                    rec.tin_id.unlink()
                    rec.tin_id = False

    def _check_tin_unique(self):
        for rec in self:
            if rec.vat:
                if rec.is_customer:
                    dup_customers = self.env['res.partner'].search_count([
                        ('id', '!=', rec.id),
                        ('is_customer', '=', True),
                        ('vat', '=', rec.vat),
                        ('company_id','=',rec.company_id.id)
                    ])
                    if dup_customers > 0:
                        raise ValidationError("Duplicate TIN Number (VAT) for customers.")
                if rec.is_vendor:
                    dup_vendors = self.env['res.partner'].search_count([
                        ('id', '!=', rec.id),
                        ('is_vendor', '=', True),
                        ('vat', '=', rec.vat),
                        ('company_id','=',rec.company_id.id)
                    ])
                    if dup_vendors > 0:
                        raise ValidationError("Duplicate TIN Number (VAT) for vendors.")

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        res._inverse_vat()
        res._check_tin_unique()
        return res

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        self._inverse_vat()
        self._check_tin_unique()
        return res

    @api.onchange('is_vendor')
    def change_vendor_rank(self):
        vend = self.env['res.partner'].search([('id', '=', self.id.origin)])
        if not self.is_vendor:
            vend.supplier_rank = 0
        else:
            vend.supplier_rank = 1

    @api.onchange('is_customer')
    def chang_cust_rank(self):
        vend = self.env['res.partner'].search([('id', '=', self.id.origin)])
        if not self.is_customer:
            vend.customer_rank = 0
        else:
            vend.customer_rank = 1


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    tin_id = fields.Many2one('partner.tin', string="TIN")

    @api.model
    def create(self, vals):
        if 'partner_id' in vals and vals.get('partner_id'):
            partner = self.env['res.partner'].browse(vals['partner_id'])
            if partner.tin_id:
                vals['tin_id'] = partner.tin_id.id
        return super(SaleOrder, self).create(vals)

    @api.onchange('tin_id')
    def _onchange_tin_id(self):
        if self.tin_id:
            self.partner_id = self.tin_id.partner_id

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id:
            self.tin_id = self.partner_id.tin_id
        else:
            self.tin_id = False

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    tin_id = fields.Many2one('partner.tin', string="TIN")

    @api.model
    def create(self, vals):
        if 'partner_id' in vals and vals.get('partner_id'):
            partner = self.env['res.partner'].browse(vals['partner_id'])
            if partner.tin_id:
                vals['tin_id'] = partner.tin_id.id
        return super(PurchaseOrder, self).create(vals)

    @api.onchange('tin_id')
    def _onchange_tin_id(self):
        if self.tin_id:
            self.partner_id = self.tin_id.partner_id

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.tin_id = self.partner_id.tin_id
        else:
            self.tin_id = False

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tin_id = fields.Many2one('partner.tin', string="TIN")
    tin_id_domain = fields.Char(
        string="TIN Domain",
        compute='_compute_tin_id_domain',
        readonly=True,
        store=False
    )

    @api.depends('picking_type_id')
    def _compute_tin_id_domain(self):
        for record in self:
            if record.picking_type_id and record.picking_type_id.code == 'outgoing':
                record.tin_id_domain = "[('partner_id.is_customer', '=', True)]"
            elif record.picking_type_id and record.picking_type_id.code == 'incoming':
                record.tin_id_domain = "[('partner_id.is_vendor', '=', True)]"
            else:
                record.tin_id_domain = "[]"

    @api.model
    def create(self, vals):
        if 'partner_id' in vals and vals.get('partner_id'):
            partner = self.env['res.partner'].browse(vals['partner_id'])
            if partner.tin_id:
                vals['tin_id'] = partner.tin_id.id
        return super(StockPicking, self).create(vals)

    @api.onchange('tin_id')
    def _onchange_tin_id(self):
        if self.tin_id:
            self.partner_id = self.tin_id.partner_id
        return {'domain': {'tin_id': eval(self.tin_id_domain) if self.tin_id_domain else []}}

    @api.onchange('partner_id', 'picking_type_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.tin_id = self.partner_id.tin_id
        else:
            self.tin_id = False
        return {'domain': {'tin_id': eval(self.tin_id_domain) if self.tin_id_domain else []}}

class AccountMove(models.Model):
    _inherit = 'account.move'

    tin_id = fields.Many2one('partner.tin', string="TIN")

    @api.model
    def create(self, vals):
        if 'partner_id' in vals and vals.get('partner_id'):
            partner = self.env['res.partner'].browse(vals['partner_id'])
            if partner.tin_id:
                vals['tin_id'] = partner.tin_id.id
        return super(AccountMove, self).create(vals)

    @api.onchange('tin_id')
    def _onchange_tin_id(self):
        if self.tin_id:
            self.partner_id = self.tin_id.partner_id

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.tin_id = self.partner_id.tin_id
        else:
            self.tin_id = False




class AccountPayment(models.Model):
    _inherit = 'account.payment'

    tin_id = fields.Many2one('partner.tin', string="TIN")

    @api.model
    def create(self, vals):
        if 'partner_id' in vals and vals.get('partner_id'):
            partner = self.env['res.partner'].browse(vals['partner_id'])
            if partner.tin_id:
                vals['tin_id'] = partner.tin_id.id
        return super(AccountPayment, self).create(vals)

    @api.onchange('tin_id')
    def _onchange_tin_id(self):
        if self.tin_id:
            self.partner_id = self.tin_id.partner_id

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.tin_id = self.partner_id.tin_id
        else:
            self.tin_id = False