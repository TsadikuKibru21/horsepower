from odoo import models, fields, api
from odoo.exceptions import UserError
import io
import xlsxwriter
import base64
from odoo import _

class MonthlySalesReportWizard(models.TransientModel):
    _name = 'monthly.sales.report.wizard'
    _description = 'Monthly Sales Report Wizard'
    name = fields.Char(string="Reference", copy=False, readonly=True, default=lambda self: _('New'))

    start_date = fields.Date(string='Start Date', default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', default=fields.Date.context_today)
    sales_team_ids = fields.Many2many('crm.team', string='Sales Teams')

    @api.model
    def create(self, vals):
        record = super(MonthlySalesReportWizard, self).create(vals)
        if not record.name or record.name == '/' or record.name == "New":
            record.name = self.env['ir.sequence'].next_by_code('monthly.sales.report.wizard')
        return record

    def action_generate_xlsx(self):
        start_date = self.start_date
        end_date = self.end_date
        if start_date and end_date and start_date > end_date:
            raise UserError(_("Start date must be before or equal to end date."))
        if not start_date or not end_date:
            start_date = False
            end_date = False

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Define styles
        title_style = workbook.add_format({'font_name': 'Arial', 'font_size': 16, 'bold': True, 'align': 'center'})
        header_style = workbook.add_format({
            'font_name': 'Arial',
            'bold': True,
            'border': 1,
            'align': 'center',
            'bg_color': '#D3D3D3',
            'font_size': 11
        })
        text_style = workbook.add_format({'font_name': 'Arial', 'border': 1, 'align': 'left'})
        number_style = workbook.add_format({'font_name': 'Arial', 'border': 1, 'align': 'right', 'num_format': '#,##0.00'})
        bold_text = workbook.add_format({'font_name': 'Arial', 'bold': True, 'align': 'left'})
        status_header = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 14, 'bg_color': '#E6E6FA'})

        sheet = workbook.add_worksheet('Sales Report')
        sheet.set_landscape()
        sheet.set_column('A:K', 12)
        sheet.set_column('C:C', 20)  # Item name wider

        # Title (row 0)
        if start_date and end_date:
            period_str = f"{start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}"
            sheet.merge_range(0, 0, 0, 10, f'Sales Report - {period_str}', title_style)
        else:
            sheet.merge_range(0, 0, 0, 10, 'Sales Report - All Time', title_style)

        # Leave a gap row for clarity
        row = 2

        # Headers row
        headers = [
            'No',
            'Client',
            'Item name',
            'Unit',
            'Quantity',
            'Unit Price',
            'Total Price',
            'Commission',
            'Cost',
            'Profit',
            'Remark'
        ]
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_style)

        # Freeze panes and autofilter for better UX
        sheet.freeze_panes(row + 1, 0)  # Freeze everything above row+1
        sheet.autofilter(row, 0, row, len(headers)-1)

        row += 1  # data starts here

        # Include empty quotation_status ('') as a valid group
        statuses = ['', 'a', 'b', 'c', 'd']
        status_labels = {'': '', 'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D'}
        total_sales_all = 0.0
        total_profit_all = 0.0
        no = 1

        # Fetch lines
        line_domain = []
        if start_date and end_date:
            line_domain += [
                ('order_id.create_date', '>=', start_date),
                ('order_id.create_date', '<=', end_date),
            ]
        if self.sales_team_ids:
            line_domain.append(('order_id.team_id', 'in', self.sales_team_ids.ids))
        sale_lines = self.env['sale.order.line'].search(line_domain, order='create_date')

        data_by_status = {}
        for line in sale_lines:
            # Ensure empty / None statuses are normalized to empty string ''
            status = line.order_id.quotation_status or ''
            if status not in data_by_status:
                data_by_status[status] = []
            qty = line.product_uom_qty
            unit_price = line.price_unit
            total_price = line.price_subtotal
            commission_percent = line.product_id.commission_percent or 0.0
            commission = total_price * (commission_percent / 100.0)
            cost = qty * (line.product_id.standard_price or 0.0)
            profit = total_price - cost
            data_by_status[status].append({
                'client': line.order_id.partner_id.name or '',
                'product_name': line.product_id.name or '',
                'unit': line.product_uom.name or '',
                'qty': qty,
                'unit_price': unit_price,
                'total_price': total_price,
                'commission': commission,
                'cost': cost,
                'profit': profit,
                'remark': '',
            })

        for status in statuses:
            if status not in data_by_status:
                continue
            # Status header (for empty status this will show "Quotation Status: " )
            sheet.merge_range(row, 0, row, 10, f'              {status_labels.get(status, status)}', status_header)
            row += 1

            for item in data_by_status[status]:
                sheet.write(row, 0, no, text_style)  # sequential number
                sheet.write(row, 1, item['client'], text_style)
                sheet.write(row, 2, item['product_name'], text_style)
                sheet.write(row, 3, item['unit'], text_style)
                sheet.write(row, 4, item['qty'], number_style)
                sheet.write(row, 5, item['unit_price'], number_style)
                sheet.write(row, 6, item['total_price'], number_style)
                sheet.write(row, 7, item['commission'], number_style)
                sheet.write(row, 8, item['cost'], number_style)
                sheet.write(row, 9, item['profit'], number_style)
                sheet.write(row, 10, item['remark'], text_style)
                total_sales_all += item['total_price']
                total_profit_all += item['profit']
                no += 1
                row += 1

        # Totals
        sheet.merge_range(row, 0, row, 6, 'Total', bold_text)
        sheet.write(row, 6, total_sales_all, number_style)
        sheet.write(row, 9, total_profit_all, number_style)
        row += 3

        # Gross uncollected cash
        invoice_domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'not in', ['paid', 'in_payment', 'reversed'])
        ]
        if start_date and end_date:
            invoice_domain += [('invoice_date', '>=', start_date), ('invoice_date', '<=', end_date)]
        if self.sales_team_ids:
            so_domain = [('team_id', 'in', self.sales_team_ids.ids)]
            if start_date and end_date:
                so_domain += [('date_order', '>=', start_date), ('date_order', '<=', end_date)]
            sale_orders = self.env['sale.order'].search(so_domain)
            invoice_ids = sale_orders.mapped('invoice_ids').ids
            invoice_domain.append(('id', 'in', invoice_ids))
        uncollected_cash = sum(self.env['account.move'].search(invoice_domain).mapped('amount_residual'))

        row += 3

        # Executive Summary
        summary_row = row
        sheet.merge_range(summary_row, 0, summary_row, 1, 'Gross uncollected cash', header_style)
        sheet.merge_range(summary_row, 2, summary_row, 3, 'Total Sales', header_style)
        sheet.merge_range(summary_row, 4, summary_row, 5, 'Total Profit', header_style)
        sheet.merge_range(summary_row, 6, summary_row, 7, 'No. of Quotations Offered', header_style)
        sheet.merge_range(summary_row, 8, summary_row, 9, 'No. of Quotations Succeeded', header_style)
        sheet.write(summary_row, 10, 'Success Rate', header_style)
        summary_row += 1

        q_domain = [('state', 'in', ['draft', 'sent','to_approve','approved','sale','done'])]
        if start_date and end_date:
            q_domain += [('create_date', '>=', start_date), ('create_date', '<=', end_date)]
        if self.sales_team_ids:
            q_domain.append(('team_id', 'in', self.sales_team_ids.ids))
        q_offered = self.env['sale.order'].search_count(q_domain)

        q_s_domain = [('state', '=', 'sale')]
        if start_date and end_date:
            q_s_domain += [('create_date', '>=', start_date), ('create_date', '<=', end_date)]
        if self.sales_team_ids:
            q_s_domain.append(('team_id', 'in', self.sales_team_ids.ids))
        q_succeeded = self.env['sale.order'].search_count(q_s_domain)

        success_rate = (q_succeeded / q_offered * 100) if q_offered else 0
        sheet.merge_range(summary_row, 0, summary_row, 1, uncollected_cash, number_style)
        sheet.merge_range(summary_row, 2, summary_row, 3, total_sales_all, number_style)
        sheet.merge_range(summary_row, 4, summary_row, 5, total_profit_all, number_style)
        sheet.merge_range(summary_row, 6, summary_row, 7, q_offered, number_style)
        sheet.merge_range(summary_row, 8, summary_row, 9, q_succeeded, number_style)
        sheet.write(summary_row, 10, f"{success_rate:.2f}%", number_style)

        # Signatures
        sig_row = summary_row + 3
        sheet.merge_range(sig_row, 0, sig_row, 2, 'Prepared by:', bold_text)
        sheet.merge_range(sig_row, 4, sig_row, 6, 'Checked by:', bold_text)
        sheet.merge_range(sig_row, 8, sig_row, 10, 'Approved by:', bold_text)

        workbook.close()
        output.seek(0)
        report_data = output.read()
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': f'monthly_sale_report_{self.name}.xlsx',
            'type': 'binary',
            'datas': base64.encodebytes(report_data),
            'store_fname': f'monthly_sale_report_{self.name}.xlsx',
            'res_model': 'monthly.sales.report.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=ir.attachment&id={attachment.id}&field=datas&filename_field=name&download=true',
            'target': 'self',
        }
