# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class InvoiceCustomerPaymentLine(models.TransientModel):
    _inherit = "invoice.customer.payment.line"

    @api.onchange("payment_difference_handling")
    def onchange_payment_diff_handling(self):
        """
        Special case: When payment diff amount is 0, payment difference
        handling should be in 'open' action
        """
        if (
            self.payment_difference_handling
            and self.payment_difference_handling == "reconcile"
            and self.payment_difference == 0.0
        ):
            # Change handling difference
            self.payment_difference_handling = "open"

    @api.onchange("payment_difference")
    def onchange_payment_difference(self):
        """
        Special case: When payment diff amount is 0, payment difference
        handling should be in 'open' action
        """
        if (
            self.payment_difference_handling
            and self.payment_difference_handling == "reconcile"
            and self.payment_difference == 0.0
        ):
            # Change handling difference
            self.payment_difference_handling = "open"

    @api.onchange("receiving_amt")
    def onchange_receiving_amt(self):
        rec = self

        # is discount applicable
        payment_date = fields.Date.from_string(rec.wizard_id.payment_date)
        discount_information = (
            rec.invoice_id.invoice_payment_term_id._check_payment_term_discount(
                rec.invoice_id, payment_date
            )
        )
        discount_amount = discount_information[0]
        discount_account_id = discount_information[1]
        payment_amount = discount_information[2] - discount_amount

        if self._context.get("reset_autofill", False):
            rec.receiving_amt = payment_amount

        # compute difference
        due_or_balance = rec.balance_amt - rec.receiving_amt

        # apply discount
        if due_or_balance <= discount_amount:
            overpayment = discount_amount - due_or_balance
            rec.payment_difference = discount_amount - overpayment
            rec.payment_difference_handling = "reconcile"
            rec.writeoff_account_id = False
            rec.note = ""

            if due_or_balance:
                rec.writeoff_account_id = discount_account_id
                rec.note = "Early Pay Discount"

        # cannot apply discount
        else:
            rec.payment_difference = due_or_balance
            rec.payment_difference_handling = "open"
            rec.writeoff_account_id = False
            rec.note = False
