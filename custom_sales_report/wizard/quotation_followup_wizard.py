# models/quotation_followup_wizard.py
from odoo import models, fields, api,_
from odoo.exceptions import UserError
import io
import xlsxwriter
import base64

class QuotationFollowupWizard(models.TransientModel):
    _name = 'quotation.followup.wizard'
    _description = 'Quotation Follow-up Wizard'
    name = fields.Char(string="Reference", copy=False, readonly=True,default=lambda self: _('New'))

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    file_data = fields.Binary('File')
    file_name = fields.Char('File Name')
    
    @api.model
    def create(self, vals):
        # Call the super method to create the advance.payment record
        record = super(QuotationFollowupWizard, self).create(vals)
        # if 'name' not in vals or vals['name'] == '/':
        if not record.name or record.name == '/' or record.name =="New":
           record.name = self.env['ir.sequence'].next_by_code('quotation.followup.wizard')
        
       
        return record

    def action_generate_xlsx(self):
        if self.start_date > self.end_date:
            raise UserError("Start date must be before or equal to end date.")
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        # Define styles
        title_style = workbook.add_format({'font_name': 'Arial', 'font_size': 14, 'bold': True, 'align': 'center'})
        subtitle_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'italic': True, 'align': 'center'})
        header_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'border': 1, 'align': 'center'})
        text_style = workbook.add_format({'font_name': 'Arial', 'border': 1, 'align': 'left'})
        date_style = workbook.add_format({'font_name': 'Arial', 'border': 1, 'num_format': 'dd-mm-yyyy'})
        currency_style = workbook.add_format({'font_name': 'Arial', 'border': 1, 'num_format': '$#,##0.00'})
        total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'border': 1, 'align': 'right'})

        sheet = workbook.add_worksheet('Quotation Follow-up Report')
        if self.start_date and self.end_date:
            subtitle = f"From {self.start_date.strftime('%d-%m-%Y')} To {self.end_date.strftime('%d-%m-%Y')}"
            sheet.merge_range('A2:K2', subtitle, subtitle_style)
        sheet.set_landscape()
        sheet.set_column('A:K', 15)

        # Title
        sheet.merge_range('A1:K1', 'Quotation Follow-up Report', title_style)

        # Headers
        headers = [
            'Quotation Source',
            'Quotation Number',
            'Date',
            'Client Name',
            'Phone Number',
            'Quotation Short Description',
            'Quotation Amount',
            'Estimated Profit',
            'Status',
            'Last Date of Follow Up',
            'Today'
        ]
        for col, header in enumerate(headers):
            sheet.write(3, col, header, header_style)

        # Get data
        domain = [
            ('state', 'in', ['draft', 'sent', 'to_approve', 'approved', 'done']),
        ]
        if self.start_date:
            domain.append(('date_order', '>=', self.start_date))
        if self.end_date:
            domain.append(('date_order', '<=', self.end_date))
        quotations = self.env['sale.order'].search(domain, order='date_order desc')

        row = 4
        today = fields.Date.today()
        grouped_data = {}
        for quo in quotations:
            status = 'WIN' if quo.state in ['sale', 'done'] else 'QUOTATION OFFERED'
            q_status = (quo.quotation_status or '').upper()
            if q_status not in grouped_data:
                grouped_data[q_status] = []
            grouped_data[q_status].append((quo, status))
        group_header_style = workbook.add_format({
            'font_name': 'Arial',
            'bold': True,
            'border': 1,
            'align': 'center',
            'bg_color': '#D9D9D9'   # light gray background
        })

        # Write grouped data by quotation_status
        for q_status, quo_list in grouped_data.items():
            # Section title
            sheet.merge_range(row, 0, row, len(headers)-1, q_status, group_header_style)
            row += 1
            for quo, status in quo_list:
                last_followup = quo.last_followup_date
                sheet.write(row, 0, quo.source_id.name or '', text_style)
                sheet.write(row, 1, quo.name, text_style)
                sheet.write(row, 2, quo.date_order, date_style)
                sheet.write(row, 3, quo.partner_id.name or '', text_style)
                sheet.write(row, 4, quo.partner_id.phone or '', text_style)
                sheet.write(row, 5, quo.quotation_description or '', text_style)
                sheet.write(row, 6, quo.amount_total, currency_style)
                sheet.write(row, 7, quo.margin, currency_style)
                sheet.write(row, 8, status, text_style)
                if last_followup:
                    sheet.write(row, 9, last_followup, date_style)
                else:
                    sheet.write(row, 9, '', text_style)
                sheet.write(row, 10, today, date_style)
                row += 1

        # Add totals row
        sheet.write(row, 5, "TOTAL", total_style)
        sheet.write_formula(row, 6, f"=SUM(G5:G{row})", currency_style)  # Quotation Amount
        sheet.write_formula(row, 7, f"=SUM(H5:H{row})", currency_style)  # Estimated Profit

        workbook.close()
        output.seek(0)
        report_data = output.read()
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': f'quotation_followup_{self.name}.xlsx',
            'type': 'binary',
            'datas': base64.encodebytes(report_data),
            'store_fname': f'quotation_followup_{self.name}.xlsx',
            'res_model': 'quotation.followup.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=ir.attachment&id={attachment.id}&field=datas&filename_field=name&download=true',
            'target': 'self',
        }


