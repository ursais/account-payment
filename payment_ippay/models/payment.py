"""Ippay Payment."""
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests
import xmltodict
from datetime import datetime
from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError


class PaymentAcquirerIppay(models.Model):
    """Ippay Payment acquirer."""

    _inherit = "payment.acquirer"

    provider = fields.Selection(selection_add=[("ippay", "IPpay")])
    api_url = fields.Char(
        "Api URL",
        required_if_provider="ippay")
    ippay_terminal_id = fields.Char(
        "IPpay TerminalID",
        required_if_provider="ippay")
    ippay_save_token = fields.Selection([
        ('none', 'Never'),
        ('ask', 'Let the customer decide'),
        ('always', 'Always')],
        string='Save Cards', default='none',
        help="This option allows customers to save their credit card "
             "as a payment token and to reuse it for a later purchase. "
             "If you manage subscriptions (recurring invoicing), "
             "you need it to automatically charge the customer when you "
             "issue an invoice.")

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super()._get_feature_support()
        res['tokenize'].append('ippay')
        return res

    @api.model
    def ippay_s2s_form_process(self, data):
        """Get Payment token ref from Ippay payment token."""
        Token = self.env["payment.token"]
        token_id = data.get("selected_token_id")
        if not token_id:
            save_token = (
                self.ippay_save_token == 'always' or
                (self.ippay_save_token == 'ask' and
                 bool(data.get('save_token')))
            )
            values = {
                "save_token": save_token,
                "cc_number": data.get("cc_number"),
                "cc_holder_name": data.get("cc_holder_name"),
                "cc_expiry": data.get("cc_expiry"),
                "cc_cvc": data.get("cc_cvc"),
                "cc_brand": data.get("cc_brand"),
                "acquirer_id": int(data.get("acquirer_id")),
                "partner_id": int(data.get("partner_id")),
            }
            # Only create a new Token if it doesn't already exist
            token_code = Token._ippay_get_token(values)
            payment_method = Token.sudo().search(
                [
                    ("acquirer_ref", "=", token_code),
                    ("partner_id", "=", values.get("partner_id")),
                    ("acquirer_id", "=", values.get("acquirer_id")),
                ],
                limit=1,
            )
            if not payment_method:
                payment_method = Token.sudo().create(values)
        else:
            payment_method = Token.sudo().browse(int(token_id))
        return payment_method

    @api.multi
    def ippay_s2s_form_validate(self, data):
        """Check the validation of card details elements."""
        error = dict()
        token_id = data.get("selected_token_id")
        if not token_id:
            mandatory_fields = [
                "cc_number",
                "cc_cvc",
                "cc_holder_name",
                "cc_expiry",
                "cc_brand",
            ]
            # Validation
            for field_name in mandatory_fields:
                if not data.get(field_name):
                    error[field_name] = "missing"
            if data["cc_expiry"]:
                # FIX we split the date into their components
                # and check if there is two components containing only digits
                # this fixes multiples crashes, if there was no space
                # between the '/' and the components the code was crashing
                # the code was also crashing if the customer
                # was proving non digits to the date.
                cc_expiry = [i.strip() for i in data["cc_expiry"].split("/")]
                all_digits = all(i.isdigit() for i in cc_expiry)
                if len(cc_expiry) != 2 or not all_digits:
                    return False
                try:
                    if datetime.now().strftime("%y%m") > datetime.strptime(
                        "/".join(cc_expiry), "%m/%y"
                    ).strftime("%y%m"):
                        return False
                except ValueError:
                    return False
            return False if error else True
        return True


class PaymentToken(models.Model):
    """
    Ippay payment token.
    """

    _inherit = "payment.token"

    # By default, keep the Token for future transactions
    # This is the case when creating from the backend
    # When collected from the Portal, the user is asked,
    # and it may be set to False to be used only for the current transaction
    save_token = fields.Boolean(default=True)
    expiry_date = fields.Date()

    @api.model
    def _ippay_get_token(self, values):
        acquirer = self.env["payment.acquirer"].browse(values["acquirer_id"])
        expiry = (values["cc_expiry"]).split("/")
        if values.get("cc_number"):
            values["cc_number"] = values["cc_number"].replace(" ", "")
            card_detail = {
                "cc_number": values["cc_number"],
                "expiry_month":
                    values.get("cc_expiry_month") or
                    expiry[0].replace(" ", ""),
                "expiry_year":
                    values.get("cc_expiry_year") or
                    expiry[1].replace(" ", ""),
            }

            xml = """<ippay>
            <TransactionType>TOKENIZE</TransactionType>
            <TerminalID>%s</TerminalID>
            <CardNum>%s</CardNum>
            <CardExpMonth>%s</CardExpMonth>
            <CardExpYear>%s</CardExpYear>
            </ippay>""" % (
                acquirer.ippay_terminal_id,
                card_detail.get("cc_number"),
                card_detail.get("expiry_month"),
                card_detail.get("expiry_year"),
            )
            if acquirer.api_url:
                url = acquirer.api_url
            r = requests.post(url, data=xml, headers={
                              "Content-Type": "text/xml"})
            data = xmltodict.parse(r.content)
            token = data["IPPayResponse"].get("Token")
            if not token:
                raise ValidationError(
                    _("Customer payment token creation in IPpay failed: %s")
                    % (data["IPPayResponse"].get("ErrMsg"))
                )
            else:
                return token

    @api.model
    def ippay_create(self, values, token_code=False):
        """Ippay token reference create."""
        # Search if the card was already stored
        # We use the last four digits for this
        existing = self.sudo().search(
            [("partner_id", "=", values.get("partner_id")),
             ("acquirer_id", "=", values.get("acquirer_id"))]
            ).filtered(lambda s: s.name[-4:] == values["cc_number"][:-4])
        if existing:
            raise ValidationError(
                _("This payment method is already assigned to this Customer.")
            )
        # In case we already know the token assigned, just use it
        token_code = token_code or self._ippay_get_token(values)
        expiry_date = fields.Date.end_of(
                fields.Date.to_date(
                    '20%s-%s-01' %  # Beware year 2100!
                    (values["cc_expiry_year"], values["cc_expiry_month"])),
                'month')
        return {
            "name": "XXXXXXXXXXXX%s - %s"
            % (values["cc_number"][-4:], values["cc_holder_name"]),
            "acquirer_ref": token_code,
            "expiry_date": expiry_date,
        }
