# __manifest__.py
{
    'name': 'Petty Cash Management',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Custom Petty Cash Management Module',
    'description': """
        This module provides custom petty cash management with request, approval, 
        expense tracking, refund/replenishment, and closing functionality.
    """,
    'author': 'Your Company',
    'depends': ['base', 'account'],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/petty_cash_custom_views.xml',
        'wizards/petty_cash_refund_close.xml',
        'data/data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}