# -*- coding: utf-8 -*-
{
    'name': "HorsePower Is Customer Is Vendor",

    'summary': """
        Customer Vendor Distribution""",
    'description': """
        This module is used to add Support work in contact form inside of Sales & Purchase Tab
    """,
    'version': '17.0',
    "author": "One Stop Odoo",
    "website": "https://onestopodoo.com",
    "maintainer": "One Stop Odoo",
    'license': 'AGPL-3',
    # any module necessary for this one to work correctly
    'depends': ['base', 'account','purchase','sale','stock'],
    'data': [
         "security/ir.model.access.csv",
         "security/security.xml",
        'views/res_partner_ext.xml',
        'views/account_move_ext.xml',
        'views/purchase_order_ext.xml',
        'views/sale_order_ext.xml',
    ],
   "images": [
        'static/description/banner.gif',
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True
    # always loaded
}
