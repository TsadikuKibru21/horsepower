{
    'name': 'Payment Order and CPV',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Custom module for Payment Order and Cheque Payment Voucher',
    'depends': ['base', 'account','mail','store_request'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/payment_order_cpv_views.xml',
        'views/account_move_template.xml',
        'reports/payment_order_report.xml',
        'reports/cpv_report.xml',
        'data/sequence.xml'
    ],
    'installable': True,
    'application': False,
}