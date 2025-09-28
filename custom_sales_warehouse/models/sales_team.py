from odoo import models,fields,api

class SaleTeam(models.Model):

    _inherit='crm.team'

    team=fields.Selection([
        ('direct_sales','Direct Sales'),
        ('estimated_tender','Estimated Tender'),
    ],string="Team")