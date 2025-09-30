{
    'name': 'Purchase Request',
    'version': '17.0',
    'summary': 'Manage store and purchase requests',
    'description': 'A module to handle store and purchase requests in Odoo',
    'depends': ['base', 'product','stock','purchase','mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        
        'data/data.xml',
       
        'views/purchase_order.xml',
        'report/purchase_request.xml',
      
     
    ],
   
    'installable': True,
    'application': True,
}
