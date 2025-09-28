from odoo import api, fields, models

class FsNumber(models.Model):
    _name = 'fs.number'
    _description = 'FS Number'
    _order = 'id desc'

    name = fields.Char(string="FS Number", required=True)
    advance_payment_id = fields.Many2one(
        'advance.payment',
        string="Advance Payment"
    )
    partner_id = fields.Many2one(
        'res.partner',
        related="advance_payment_id.partner_id",
        store=True,
        string="Partner"
    )

class MachineCode(models.Model):
    _name="machine.code"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name=fields.Char(string="Name")
    active=fields.Boolean(string="",default=True)