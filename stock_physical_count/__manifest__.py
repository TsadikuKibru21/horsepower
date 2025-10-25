# __manifest__.py
{
    'name': 'HorsePower Physical Count Custom',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Manage physical count lines with calculated differences',
    'description': """
        This module provides a model for physical count lines, including fields for
        item code, product, location, quantities, and a computed difference.
    """,
    'author': 'Your Name',
    'depends': ['stock'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/physical_count_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}