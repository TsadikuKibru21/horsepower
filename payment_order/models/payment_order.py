from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import float_round

import logging
_logger = logging.getLogger(__name__)
class AccountMove(models.Model):
    _inherit='account.move'

    fs_number = fields.Many2many(
        'fs.number',
        'account_move_fs_number_rel',  # relation table name
        'move_id',                     # field for account.move
        'fs_number_id',                # field for fs.number
        string="FS Numbers",
        track_visibility='always',
        domain="[('partner_id', '=', partner_id)]",
    )
    
    machine_code= fields.Many2one(
    'machine.code',
    string="Machine Code",
    track_visibility='always'
)
    payment_code = fields.Selection([
        ('cash', 'Cash or Transfer'),
        ('cheque', 'Cheque'),
        ('cpo', 'CPO')
    ], default='cash',track_visibility='always')
    cheque_no=fields.Char(string='Cheque No')
    cpo_no=fields.Char(string='CPO No')
    description=fields.Char(string="Description")
    pay_to = fields.Char(string='Pay To')
    def action_post(self):
        res = super().action_post()

        for move in self:
            if move.fs_number:
                fs_names = ", ".join(move.fs_number.mapped("name"))
                odoo_set_line = move.line_ids.filtered(lambda line: line.name == move.name)
                if odoo_set_line:

                # Update move lines with FS number instead of default reference
                    odoo_set_line.write({'name': fs_names})

        return res
    

class AdvancePayment(models.Model):
    _name = 'advance.payment'
    _description = 'Advance Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    # _rec_name = 'partner_id'
    name = fields.Char(string="Reference", copy=False, readonly=True,default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Partner',track_visibility='always')
    amount = fields.Float(string='B. VAT', required=True,track_visibility='always')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today,track_visibility='always')
    journal_id = fields.Many2one('account.journal', domain="[('id', 'in', available_journal_ids)]", string='Bank',track_visibility='always')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    tax_amount=fields.Float(string="Tax Amount",compute="_compute_net_amount")
    net_amount=fields.Float(string="Total Amount",compute="_compute_net_amount")
    advance_type = fields.Selection([
        ('send', 'Send'),
        ('receive', 'Receive')
    ], string='Type', required=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('validated', 'Validated')
    ], default='draft',track_visibility='always')
    payment_id = fields.Many2one('account.payment', string='Related Payment', readonly=True)
    active=fields.Boolean(string="",default=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    
    tax_ids = fields.Many2many('account.tax', string="Taxes",track_visibility='always', )
    
    fs_number= fields.Many2one(
    'fs.number',
    string="FS Number",
    track_visibility='always'
)
    machine_code= fields.Many2one(
    'machine.code',
    string="Machine Code",
    track_visibility='always'
)
    
    journal_count=fields.Integer(string="",compute="_compute_journal_count")
    available_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        compute='_compute_available_journal_ids'
    )
    
    multiple_bank = fields.Boolean(string="Banks", track_visibility='always')
    advance_payment_line_ids = fields.One2many('advance.payment.line', 'advance_payment_id', string="Bank Lines", track_visibility='always')
    date=fields.Date(string="Date",default=fields.Date.today())
    agent_id=fields.Many2one('res.users',string="Agent")
    ft = fields.Char(string='FT')
    memo = fields.Char(string='Memo')
    use_previous_fs=fields.Boolean(string="Use Previous FS")

    description=fields.Char(string="Description")
    pay_to = fields.Char(string='Pay To')
    payment_code = fields.Selection([
        ('cash', 'Cash or Transfer'),
        ('cheque', 'Cheque'),
        ('cpo', 'CPO')
    ], default='cash',track_visibility='always')
    cheque_no=fields.Char(string='Cheque No')
    cpo_no=fields.Char(string='CPO No')
    tin_id = fields.Many2one('partner.tin', string="TIN")
    
    @api.onchange('tin_id')
    def _onchange_tin_id(self):
        if self.tin_id:
            self.partner_id = self.tin_id.partner_id
            
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.tin_id = self.partner_id.tin_id
            
   
    
    @api.constrains('amount', 'net_amount', 'advance_payment_line_ids', 'multiple_bank')
    def _check_amounts(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("The Untaxed Amount must be greater than zero."))
            if rec.net_amount <= 0:
                raise ValidationError(_("The Net Amount must be greater than zero."))
            if rec.multiple_bank:
                line_total = sum(line.amount for line in rec.advance_payment_line_ids)
                if round(line_total, 2) != round(rec.net_amount, 2):
                    raise ValidationError(_(
                        "The total amount of bank lines (%s) must equal the Total Amount (%s)."
                    ) % (line_total, rec.net_amount))
   
   
   
   
    @api.depends('advance_type')
    def _compute_available_journal_ids(self):
        """Get all journals having at least one payment method for inbound/outbound."""
        Journal = self.env['account.journal']
        journals = Journal.search([
            '|',
            ('company_id', 'parent_of', self.env.company.id),
            ('company_id', 'child_of', self.env.company.id),
            ('type', 'in', ('bank', 'cash', 'credit')),
        ])
        for rec in self:
            if rec.advance_type == 'receive':  # inbound
                rec.available_journal_ids = journals.filtered('inbound_payment_method_line_ids')
            else:    # outbound
                rec.available_journal_ids = journals.filtered('outbound_payment_method_line_ids')
            

    @api.depends('move_id')
    def _compute_journal_count(self):
        for record in self:
            record.journal_count=len(self.env['account.move'].search([
                ('id','=',record.move_id.id)
            ]))
    
    @api.constrains('amount', 'net_amount')
    def _check_amounts_positive(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("The Amount must be greater than zero."))
            # net_amount is computed so can be <=0 if tax/other_income is big, so check only if positive net is expected
            if rec.net_amount <= 0:
                raise ValidationError(_("The Net Amount must be greater than zero."))

    
    @api.depends('amount', 'tax_ids')
    def _compute_net_amount(self):
        for record in self:
            currency_precision = record.currency_id.decimal_places or 2
            # Tax calculation
            tax_value = 0.0
            for tax in record.tax_ids:
                if tax.amount_type == 'percent':
                    tax_value += float_round((record.amount * tax.amount) / 100.0, precision_digits=currency_precision)
                elif tax.amount_type == 'fixed':
                    tax_value += float_round(tax.amount, precision_digits=currency_precision)

            record.tax_amount = float_round(tax_value, precision_digits=currency_precision)
            record.net_amount = float_round(record.amount + tax_value, precision_digits=currency_precision)
    
    
    @api.model
    def create(self, vals):
        # Call the super method to create the advance.payment record
        record = super(AdvancePayment, self).create(vals)
        # if 'name' not in vals or vals['name'] == '/':
        if not record.name or record.name == '/' or record.name =="New":
           record.name = self.env['ir.sequence'].next_by_code('advance.payment')
        
        # If fs_number is provided, link it to the newly created advance.payment
        if vals.get('fs_number'):
            fs_number = self.env['fs.number'].browse(vals.get('fs_number'))
            if fs_number and not fs_number.advance_payment_id:
                fs_number.write({'advance_payment_id': record.id})
        _logger.info("################### vals")
        _logger.info(vals)
        partner=self.env['res.partner'].browse(vals.get('partner_id'))
        
        if partner.company_id:
            if partner.company_id.id != self.env.company.id:
                raise ValidationError("The Customer / Vendor is not For this Company")
        return record
    
    @api.model
    def write(self, vals):
        # Call the super method to create the advance.payment record
        record = super(AdvancePayment, self).write(vals)
        # if 'name' not in vals or vals['name'] == '/':
    
        # If fs_number is provided, link it to the newly created advance.payment
        if vals.get('fs_number'):
            fs_number = self.env['fs.number'].browse(vals.get('fs_number'))
            if fs_number and not fs_number.advance_payment_id:
                fs_number.write({'advance_payment_id': self.id})
        
        return record
    

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Determine type from context
        menu_type = self.env.context.get('default_advance_type')
        if menu_type:
            res['advance_type'] = menu_type
        return res

    def create_journal(self):
        for rec in self:
            if rec.state != 'submitted':
                raise ValidationError("Only Submitted Advance Payment is Validated")
            if rec.move_id:
                rec.move_id.unlink()
            if not rec.journal_id:
                raise ValidationError(_("Please Set Journal"))
            if not rec.partner_id:
                raise ValidationError(_("Please Set Partner"))
            if (not rec.fs_number or not rec.machine_code) and rec.advance_type == 'receive':
                raise ValidationError(_("Please Set FS Number and Machine Code"))

            payment_type = 'inbound' if rec.advance_type == 'receive' else 'outbound'
            payment_method_line = self.env['account.payment.method.line'].search([
                ('journal_id', '=', rec.journal_id.id),
                ('payment_account_id', '!=', False),
                ('payment_method_id.payment_type', '=', payment_type)
            ], limit=1)

            if not payment_method_line:
                raise ValidationError(_(
                    "No payment method line found for %s payments in journal '%s'. "
                    "Please configure a payment method for %s payments."
                ) % (payment_type, rec.journal_id.name, payment_type))

            if not payment_method_line.payment_account_id:
                raise ValidationError(_(
                    "Journal '%s' must have an outstanding receipt account configured for %s payments."
                ) % (rec.journal_id.name, payment_type))

            bank_account_id = payment_method_line.payment_account_id.id
            partner_account_id = (
                rec.partner_id.property_account_receivable_id.id
                if rec.advance_type == 'receive'
                else rec.partner_id.property_account_payable_id.id
            )
            if not partner_account_id:
                raise ValidationError(_("Partner must have a receivable or payable account configured."))

            move_lines = []
            currency_precision = rec.currency_id.decimal_places or 3  # Use currency's precision (default to 2)

            # Reference for journal entry
            if rec.fs_number and rec.machine_code:
                ref = f"{rec.fs_number.name} / {rec.machine_code.name}"
            elif rec.fs_number:
                ref = rec.fs_number.name
            else:
                ref = f"{rec.memo}"

            # Handle multiple bank lines
            if rec.multiple_bank:
                if not rec.advance_payment_line_ids:
                    raise ValidationError(_("No bank lines provided when multiple banks are enabled."))

                total_debit = 0.0
                total_credit = 0.0

                # Bank lines
                for line in rec.advance_payment_line_ids:
                    line_amount = float_round(line.amount, precision_digits=currency_precision)
                    move_lines.append((0, 0, {
                        'account_id': bank_account_id,
                        'partner_id': rec.partner_id.id,
                        'name': rec.ft,
                        'debit': line_amount if rec.advance_type == 'receive' else 0.0,
                        'credit': 0.0 if rec.advance_type == 'receive' else line_amount,
                        'currency_id': rec.currency_id.id,
                        'company_id': rec.company_id.id,
                    }))
                    total_debit += line_amount if rec.advance_type == 'receive' else 0.0
                    total_credit += line_amount if rec.advance_type == 'outbound' else 0.0

                
                partner_amount = float_round(rec.amount, precision_digits=currency_precision)
                if rec.advance_type == 'receive':
                    move_lines.append((0, 0, {
                        'account_id': partner_account_id,
                        'partner_id': rec.partner_id.id,
                        'name': rec.description,
                        'debit': 0.0,
                        'credit': partner_amount,
                        'currency_id': rec.currency_id.id,
                        'company_id': rec.company_id.id,
                    }))
                    total_credit += partner_amount
                else:
                    move_lines.append((0, 0, {
                        'account_id': partner_account_id,
                        'partner_id': rec.partner_id.id,
                        'name': rec.description,
                        'debit': partner_amount,
                        'credit': 0.0,
                        'currency_id': rec.currency_id.id,
                        'company_id': rec.company_id.id,
                    }))
                    total_debit += partner_amount

                # Regular taxes (non-intercompany)
                for tax in rec.tax_ids:
                    tax_amount = float_round(
                        (rec.amount * tax.amount / 100.0 if tax.amount_type == 'percent' else tax.amount),
                        precision_digits=currency_precision
                    )
                    if tax_amount == 0:
                        continue
                    repartition_line = tax.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax')[:1]
                    if not repartition_line or not repartition_line.account_id:
                        raise ValidationError(_("No valid account found in invoice repartition lines for tax '%s'") % tax.name)
                    if rec.advance_type == 'receive':
                        move_lines.append((0, 0, {
                            'account_id': repartition_line.account_id.id,
                            'name': f"Tax - {tax.name}",
                            'debit': 0.0 if tax.amount >= 0 else abs(tax_amount),
                            'credit': tax_amount if tax.amount >= 0 else 0.0,
                            'currency_id': rec.currency_id.id,
                            'company_id': rec.company_id.id,
                        }))
                        total_debit += 0.0 if tax.amount >= 0 else abs(tax_amount)
                        total_credit += tax_amount if tax.amount >= 0 else 0.0
                    else:
                        move_lines.append((0, 0, {
                            'account_id': repartition_line.account_id.id,
                            'name': f"Tax - {tax.name}",
                            'debit': tax_amount if tax.amount >= 0 else 0.0,
                            'credit': 0.0 if tax.amount >= 0 else abs(tax_amount),
                            'currency_id': rec.currency_id.id,
                            'company_id': rec.company_id.id,
                        }))
                        total_debit += tax_amount if tax.amount >= 0 else 0.0
                        total_credit += 0.0 if tax.amount >= 0 else abs(tax_amount)

                # Adjust the partner line to balance the entry
                diff = float_round(total_debit - total_credit, precision_digits=currency_precision)
                if diff != 0:
                    for line in move_lines:
                        if line[2]['account_id'] == partner_account_id:
                            if rec.advance_type == 'receive':
                                line[2]['credit'] = float_round(line[2]['credit'] + diff, precision_digits=currency_precision)
                            else:
                                line[2]['debit'] = float_round(line[2]['debit'] + diff, precision_digits=currency_precision)
                            break

            else:
                # Single bank line case
               
                net_amount = float_round(rec.net_amount, precision_digits=currency_precision)
                partner_amount = float_round(rec.amount, precision_digits=currency_precision)

                total_debit = 0.0
                total_credit = 0.0

                if rec.advance_type == 'receive':
                    move_lines.append((0, 0, {
                        'account_id': bank_account_id,
                        'partner_id': rec.partner_id.id,
                        'name': rec.description,
                        'debit': net_amount,
                        'credit': 0.0,
                        'currency_id': rec.currency_id.id,
                        'company_id': rec.company_id.id,
                    }))
                    total_debit += net_amount
                    move_lines.append((0, 0, {
                        'account_id': partner_account_id,
                        'partner_id': rec.partner_id.id,
                        'name': rec.description,
                        'debit': 0.0,
                        'credit': partner_amount,
                        'currency_id': rec.currency_id.id,
                        'company_id': rec.company_id.id,
                    }))
                    total_credit += partner_amount
                else:
                    move_lines.append((0, 0, {
                        'account_id': partner_account_id,
                        'partner_id': rec.partner_id.id,
                        'name': rec.description,
                        'debit': partner_amount,
                        'credit': 0.0,
                        'currency_id': rec.currency_id.id,
                        'company_id': rec.company_id.id,
                    }))
                    total_debit += partner_amount
                    move_lines.append((0, 0, {
                        'account_id': bank_account_id,
                        'partner_id': rec.partner_id.id,
                        'name': rec.description,
                        'debit': 0.0,
                        'credit': net_amount,
                        'currency_id': rec.currency_id.id,
                        'company_id': rec.company_id.id,
                    }))
                    total_credit += net_amount

                # Regular taxes (non-intercompany)
                for tax in rec.tax_ids:
                    tax_amount = float_round(
                        (rec.amount * tax.amount / 100.0 if tax.amount_type == 'percent' else tax.amount),
                        precision_digits=currency_precision
                    )
                    if tax_amount == 0:
                        continue
                    repartition_line = tax.invoice_repartition_line_ids.filtered(lambda l: l.repartition_type == 'tax')[:1]
                    if not repartition_line or not repartition_line.account_id:
                        raise ValidationError(_("No valid account found in invoice repartition lines for tax '%s'") % tax.name)
                    if rec.advance_type == 'receive':
                        move_lines.append((0, 0, {
                            'account_id': repartition_line.account_id.id,
                            'name': f"Tax - {tax.name}",
                            'debit': 0.0 if tax.amount >= 0 else abs(tax_amount),
                            'credit': tax_amount if tax.amount >= 0 else 0.0,
                            'currency_id': rec.currency_id.id,
                            'company_id': rec.company_id.id,
                        }))
                        total_debit += 0.0 if tax.amount >= 0 else abs(tax_amount)
                        total_credit += tax_amount if tax.amount >= 0 else 0.0
                    else:
                        move_lines.append((0, 0, {
                            'account_id': repartition_line.account_id.id,
                            'name': f"Tax - {tax.name}",
                            'debit': tax_amount if tax.amount >= 0 else 0.0,
                            'credit': 0.0 if tax.amount >= 0 else abs(tax_amount),
                            'currency_id': rec.currency_id.id,
                            'company_id': rec.company_id.id,
                        }))
                        total_debit += tax_amount if tax.amount >= 0 else 0.0
                        total_credit += 0.0 if tax.amount >= 0 else abs(tax_amount)

                # Adjust the partner line to balance the entry
                diff = float_round(total_debit - total_credit, precision_digits=currency_precision)
                if diff != 0:
                    for line in move_lines:
                        if line[2]['account_id'] == partner_account_id:
                            if rec.advance_type == 'receive':
                                line[2]['credit'] = float_round(line[2]['credit'] + diff, precision_digits=currency_precision)
                            else:
                                line[2]['debit'] = float_round(line[2]['debit'] + diff, precision_digits=currency_precision)
                            break

            move = self.env['account.move'].sudo().create({
                'ref': ref,
                'machine_code': rec.machine_code.id,
                'journal_id': rec.journal_id.id,
                'fs_number': [(6, 0, [rec.fs_number.id])] if rec.fs_number else False,
                'date': rec.payment_date or fields.Date.today(),
                'move_type': 'entry',
                'line_ids': move_lines,
                'company_id': rec.company_id.id,
                'tin_id': rec.tin_id.id,
                'payment_code': rec.payment_code,
                'cheque_no': rec.cheque_no,
                'cpo_no': rec.cpo_no,
                'description': rec.description,
                'pay_to': rec.pay_to
            })

            rec.write({'move_id': move.id})

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec.state = 'submitted'
    def action_validate(self):
        for rec in self:
            if not self.env.user.has_group("payment_order.group_advance_payable_validate"):
                 raise ValidationError(_("You are not allowed to Validate."))
            if rec.state != 'submitted':
                continue
            rec.create_journal()
            rec.move_id.action_post()
            rec.state = 'validated'
          
    
    def action_reset_to_draft(self):
        for rec in self:
            if rec.move_id and rec.move_id.state != 'draft':
                rec.move_id.button_draft()
            rec.state = 'draft'

    def action_view_journal(self):
        return {
        "type": "ir.actions.act_window",
        "name": "Journal",
        "res_model": "account.move",
        "view_mode": "tree,form",
        'domain': [('id', '=', self.move_id.id)],
        "target": "self"
    }

    

class AdvancePaymentLine(models.Model):
    _name = 'advance.payment.line'
    _description = 'Advance Payment Line'

    advance_payment_id = fields.Many2one('advance.payment', string='Advance Payment', required=True, ondelete='cascade')
    bank_name=fields.Many2one('res.partner.bank',string="Bank Name")
    ft = fields.Char(string='FT',required=True)
    amount = fields.Float(string='Amount', required=True)
    
    @api.constrains('ft')
    def _check_ft_length(self):
        for record in self:
            if record.ft and len(record.ft) < 10:
                raise ValidationError("FT must be at least 10 characters long.")
        
    @api.onchange('bank_name', 'amount')
    def _onchange_adjust_amounts(self):
        if not self.advance_payment_id:
            return
        advance = self.advance_payment_id
        net_amount = advance.net_amount

        # total of all lines
        total = sum(advance.advance_payment_line_ids.mapped('amount'))

        # difference to fix
        diff = round(net_amount - total, 2)

        if diff != 0:
            # try adjusting another line (not the one currently edited)
            for line in advance.advance_payment_line_ids:
                if line.id != self.id:
                    line.amount += diff
                    break
            else:
                # if only one line, adjust this one
                self.amount += diff