from odoo import models, fields, api
from odoo.http import request
import io
import xlsxwriter

import base64
from odoo.tools import date_utils

class CustomerEnquiryWizard(models.Model):
    _name = 'customer.enquiry.report'
    _description = 'Customer Enquiry Report Wizard'

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    file_data = fields.Binary('File')
    file_name = fields.Char('File Name')

    def action_generate_report(self):
        output = io.BytesIO()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        # Define styles
        title_style = workbook.add_format({'font_name': 'Arial', 'font_size': 14, 'bold': True, 'align': 'center'})
        subtitle_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'italic': True, 'align': 'center'})
        header_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'border': 1, 'align': 'center'})
        text_style = workbook.add_format({'font_name': 'Arial', 'border': 1, 'align': 'left'})
        date_style = workbook.add_format({'font_name': 'Arial', 'border': 1, 'num_format': 'dd-mm-yyyy'})

        sheet = workbook.add_worksheet('Customer Enquiry Report')
        if self.start_date and self.end_date:
            subtitle = f"From {self.start_date.strftime('%d-%m-%Y')} To {self.end_date.strftime('%d-%m-%Y')}"
            sheet.merge_range('A2:E2', subtitle, subtitle_style)
        sheet.set_landscape()
        sheet.set_column('A:E', 25)

        # Title
        sheet.merge_range('A1:E1', 'Customer Enquiry Report', title_style)

        # Headers
        headers = ['Customer', 'Product', 'Optional Product', 'Quantity','Date', 'Salesperson']
        for col, header in enumerate(headers):
            sheet.write(2, col, header, header_style)

        # Get data
        domain = []
        if self.start_date:
            domain.append(('date', '>=', self.start_date))
        if self.end_date:
            domain.append(('date', '<=', self.end_date))

        enquiries = self.env['customer.enquiry'].search(domain)
        row = 3
        for enquiry in enquiries:
            sheet.write(row, 0, enquiry.partner_id.name or '', text_style)
            sheet.write(row, 1, enquiry.product_id.name or '', text_style)
            sheet.write(row, 2, enquiry.optional_product or '', text_style)
            sheet.write(row, 3, enquiry.quantity or '', text_style)
            sheet.write(row, 4, enquiry.date, date_style)
            sheet.write(row, 5, enquiry.salesperson_id.name or '', text_style)
            row += 1

        workbook.close()
        output.seek(0)
        report_data = output.read()
        output.close()

        file_name = 'customer_enquiry_report.xlsx'
        self.write({
            'file_data': base64.b64encode(report_data),
            'file_name': file_name,
        })

        # return {
        #     'type': 'ir.actions.act_window',
        #     'res_model': 'customer.enquiry.report',
        #     'view_mode': 'form',
        #     'res_id': self.id,
        #     'views': [(False, 'form')],
        #     'target': 'new',
        # }
     
