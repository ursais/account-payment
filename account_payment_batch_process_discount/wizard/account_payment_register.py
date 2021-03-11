# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from datetime import datetime

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

try:
    from num2words import num2words
except ImportError:
    logging.getLogger(__name__).warning(
        "The num2words python library is not\
     installed."
    )
    num2words = None

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    "out_invoice": "customer",
    "out_refund": "customer",
    "in_invoice": "supplier",
    "in_refund": "supplier",
}

# Since invoice amounts are unsigned,
# this is how we know if money comes in or goes out
MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    "out_invoice": 1,
    "in_refund": 1,
    "in_invoice": -1,
    "out_refund": -1,
}


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.onchange("payment_date")
    def onchange_payment_date(self):
        if self.payment_date:
            # Check for Customer Invoice
            for rec in self.invoice_customer_payments:
                rec.with_context(reset_autofill=True).onchange_receiving_amt()

            # Check for Vendor Invoice
            for rec in self.invoice_payments:
                rec.with_context(reset_autofill=True).onchange_paying_amt()

    @api.onchange("invoice_customer_payments")
    def _get_cust_amount(self):
        tot = 0.0
        for rec in self.invoice_customer_payments:
            tot += rec.receiving_amt
        if self.invoice_customer_payments:
            self.cheque_amount = tot

    @api.onchange("invoice_payments")
    def _get_supp_amount(self):
        tot = 0.0
        for rec in self.invoice_payments:
            tot += rec.paying_amt
        if self.invoice_payments:
            self.cheque_amount = tot

    def get_batch_payment_amount(self, invoice_id=None, payment_date=None):
        val = {
            "amt": False,
            "payment_difference": False,
            "payment_difference_handling": False,
            "writeoff_account_id": False,
        }
        discount_information = invoice_id.invoice_payment_term_id._check_payment_term_discount(
            invoice_id, payment_date
        )
        discount_amt = discount_information[0]
        discount_account_id = discount_information[1]
        # compute payment difference
        payment_difference = self.payment_difference
        if payment_difference <= discount_amt:
            # Prepare val
            val.update(
                {
                    "payment_difference": discount_amt,
                    "amt": abs(invoice_id.amount_residual - discount_amt),
                    "payment_difference_handling": "reconcile",
                    "writeoff_account_id": discount_account_id,
                    "note": (payment_difference != 0.0)
                    and "Early Pay Discount"
                    or False,
                }
            )
        return val

    @api.model
    def default_get(self, fields):
        if self.env.context and not self.env.context.get("batch", False):
            return super().default_get(fields)
        rec = super(AccountPaymentRegister, self).default_get(fields)
        context = dict(self._context or {})
        active_model = context.get("active_model")
        active_ids = context.get("active_ids")
        # Checks on context parameters
        if not active_model or not active_ids:
            raise UserError(
                _(
                    "The wizard action is executed without active_model or active_ids in the context."
                )
            )
        if active_model != "account.move":
            raise UserError(
                _("The expected model for this action is 'account.move', not '%s'.")
                % active_model
            )
        # Checks on received invoice records
        invoices = self.env[active_model].browse(active_ids)
        if any(inv.payment_mode_id != invoices[0].payment_mode_id for inv in invoices):
            raise UserError(
                _(
                    "You can only register payments for invoices with the same payment mode"
                )
            )
        if any(invoice.state != "posted" for invoice in invoices):
            raise UserError(_("You can only register payments for open invoices."))
        if any(
            MAP_INVOICE_TYPE_PARTNER_TYPE[inv.move_type]
            != MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type]
            for inv in invoices
        ):
            raise UserError(
                _(
                    "You cannot mix customer invoices and vendor bills in a single payment."
                )
            )
        if any(inv.currency_id != invoices[0].currency_id for inv in invoices):
            raise UserError(
                _(
                    "In order to pay multiple invoices at once, they must use the same currency."
                )
            )
        # Set payment date as current date
        payment_date = datetime.today()

        if "batch" in context and context.get("batch"):
            payment_lines = []
            if MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type] == "customer":
                for inv in invoices:
                    # Get prepared dict
                    vals = self.get_batch_payment_amount(inv, payment_date)
                    discount_information = (
                        inv.invoice_payment_term_id._check_payment_term_discount(
                            inv, payment_date
                        )
                    )
                    discount_amt = discount_information[0]
                    if discount_information[2]:
                        payment_amount = discount_information[2] - discount_amt
                    else:
                        payment_amount = inv.amount_residual
                    payment_difference = discount_amt
                    if payment_amount <= 0.0:
                        payment_amount = vals.get("amt") or 0.0
                    if discount_amt <= 0.0:
                        payment_difference = vals.get("payment_difference") or 0.0
                    payment_lines.append(
                        (
                            0,
                            0,
                            {
                                "partner_id": inv.partner_id.id,
                                "invoice_id": inv.id,
                                "balance_amt": inv.amount_residual or 0.0,
                                "receiving_amt": payment_amount,
                                "payment_difference_handling": vals.get(
                                    "payment_difference_handling", False
                                ),
                                "payment_difference": payment_difference,
                                "writeoff_account_id": vals.get(
                                    "writeoff_account_id", False
                                ),
                                "note": vals.get("note", False),
                            },
                        )
                    )
                rec.update(
                    {"invoice_customer_payments": payment_lines, "is_customer": True}
                )
            else:
                for inv in invoices:
                    # Get prepared dict
                    vals = self.get_batch_payment_amount(inv, payment_date)
                    discount_information = (
                        inv.invoice_payment_term_id._check_payment_term_discount(
                            inv, payment_date
                        )
                    )
                    discount_amt = discount_information[0]
                    if discount_information[2]:
                        payment_amount = discount_information[2] - discount_amt
                    else:
                        payment_amount = inv.amount_residual
                    payment_difference = discount_amt
                    if payment_amount <= 0.0:
                        payment_amount = vals.get("amt")
                    if discount_amt <= 0.0:
                        payment_difference = vals.get("payment_difference") or 0.0
                    payment_lines.append(
                        (
                            0,
                            0,
                            {
                                "partner_id": inv.partner_id.id,
                                "invoice_id": inv.id,
                                "balance_amt": inv.amount_residual or 0.0,
                                "payment_difference": payment_difference,
                                "paying_amt": payment_amount,
                                "note": vals.get("note", False),
                                "writeoff_account_id": vals.get(
                                    "writeoff_account_id", False
                                ),
                                "payment_difference_handling": vals.get(
                                    "payment_difference_handling", False
                                ),
                            },
                        )
                    )
                rec.update({"invoice_payments": payment_lines, "is_customer": False})
        else:
            # Checks on received invoice records
            if any(
                MAP_INVOICE_TYPE_PARTNER_TYPE[inv.move_type]
                != MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type]
                for inv in invoices
            ):
                raise UserError(
                    _(
                        "You cannot mix customer invoices and vendor bills in a single payment."
                    )
                )

        total_amount = sum(
            inv.amount_residual * MAP_INVOICE_TYPE_PAYMENT_SIGN[inv.move_type] for inv in invoices
        )
        rec.update(
            {
                "amount": abs(total_amount),
                "currency_id": invoices[0].currency_id.id,
                "payment_type": total_amount > 0 and "inbound" or "outbound",
                "partner_id": invoices[0].commercial_partner_id.id,
                "partner_type": MAP_INVOICE_TYPE_PARTNER_TYPE[invoices[0].move_type],
                "payment_date": payment_date,
            }
        )
        return rec

    def auto_fill_payments(self):
        ctx = self._context.copy()
        # Check if payment date set
        if not self.payment_date:
            raise ValidationError(_("Please enter the payment date."))

        for wiz in self:
            if wiz.is_customer:
                if wiz.invoice_customer_payments:
                    cust_tot = 0.0
                    for payline in wiz.invoice_customer_payments:
                        vals = self.get_batch_payment_amount(
                            payline.invoice_id, self.payment_date
                        )
                        payline.write(
                            {
                                "receiving_amt": vals.get("amt", False)
                                or payline.balance_amt,
                                "payment_difference": vals.get(
                                    "payment_difference", False
                                )
                                or 0.0,
                                "writeoff_account_id": vals.get(
                                    "writeoff_account_id", False
                                ),
                                "payment_difference_handling": vals.get(
                                    "payment_difference_handling", False
                                ),
                                "note": vals.get("note", False),
                            }
                        )
                        # Special Case: If full amount payment, then make diff handling as 'reconcile'
                        if (
                            payline.payment_difference_handling == "reconcile"
                            and payline.payment_difference == 0.0
                        ):
                            # Change handling difference
                            payline.payment_difference_handling = "open"
                        cust_tot += payline.receiving_amt
                    wiz.cheque_amount = cust_tot
                ctx.update(
                    {
                        "reference": wiz.communication or "",
                        "journal_id": wiz.journal_id.id,
                    }
                )
            else:
                if wiz.invoice_payments:
                    supp_tot = 0.0
                    for payline in wiz.invoice_payments:
                        vals = self.get_batch_payment_amount(
                            payline.invoice_id, self.payment_date
                        )
                        payline.write(
                            {
                                "paying_amt": vals.get("amt", False)
                                or payline.balance_amt,
                                "payment_difference": vals.get(
                                    "payment_difference", False
                                )
                                or 0.0,
                                "writeoff_account_id": vals.get(
                                    "writeoff_account_id", False
                                ),
                                "payment_difference_handling": vals.get(
                                    "payment_difference_handling", False
                                ),
                                "note": vals.get("note", False),
                            }
                        )
                        # Special Case: If full amount payment, then make diff handling as 'reconcile'
                        if (
                            payline.payment_difference_handling == "reconcile"
                            and payline.payment_difference == 0.0
                        ):
                            # Change handling difference
                            payline.payment_difference_handling = "open"
                        supp_tot += payline.paying_amt
                    wiz.cheque_amount = supp_tot
                ctx.update(
                    {
                        "reference": wiz.communication or "",
                        "journal_id": wiz.journal_id.id,
                    }
                )
        return {
            "name": _("Batch Payments"),
            "view_mode": "form",
            "view_id": False,
            "view_type": "form",
            "res_id": self.id,
            "res_model": "account.register.payments",
            "type": "ir.actions.act_window",
            "nodestroy": True,
            "target": "new",
            "context": ctx,
        }
