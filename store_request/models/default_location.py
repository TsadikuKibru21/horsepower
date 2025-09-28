from odoo import fields,models,api,_


class DefaultLocation(models.Model):

    _inherit='stock.location'

    is_default_location=fields.Boolean(string="Default Location")