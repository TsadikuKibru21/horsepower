{
    'name': 'Payment Order',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Custom module for Payment Order and Cheque Payment Voucher',
    'depends': ['base', 'account','mail'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/payment_order.xml',
        'views/account_move_template.xml',
        'views/machine_code.xml',
      
        'data/sequence.xml',
        'report/payment.xml'
    ],
    'installable': True,
    'application': False,
}