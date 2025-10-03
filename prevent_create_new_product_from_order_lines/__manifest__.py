# -*- coding: utf-8 -*-
{
    'name': "HorsePower Prevent Create New Product from Order Lines",

    'summary': """
        Prevent users to create new product from the order lines
        """,

    'description': """
        Sometimes a user accidentally created new product from order lines such from the sales.order,
        using this module we can prevent users make the mistakes
    """,

    'author': "da Ti Soft Consulting",
    'website': "http://github.com/trinanda",
    'images': ['static/description/icon.png'],

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Utilities',
    'version': '17.0',

    # any module necessary for this one to work correctly
    'depends': ['sale', 'purchase','account','stock'],

    # always loaded
    'data': [
        'views/all.xml',
        # 'views/templates.xml',
    ],

}
