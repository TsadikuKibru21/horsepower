

from odoo import models, api,_,fields

class TendorLocation(models.Model):

    _name = 'purchase.tender.location'

    name=fields.Char(string="Name")