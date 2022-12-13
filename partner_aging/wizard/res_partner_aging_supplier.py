# Copyright 2012 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import tools
from odoo import api, fields, models


class ResPartnerAgingSupplier(models.Model):
    _name = "res.partner.aging.supplier"
    _description = "Res Partner Aging Supplier"
    _auto = False
    _order = "partner_id"

    partner_id = fields.Many2one("res.partner", "Partner", readonly=True)
    max_days_overdue = fields.Integer("Days Outstanding", readonly=True)
    avg_days_overdue = fields.Integer("Avg Days Overdue", readonly=True)
    date = fields.Date("Date", readonly=True)
    date_due = fields.Date("Due Date", readonly=True)
    inv_date_due = fields.Date("Invoice Date", readonly=True)
    total = fields.Float("Total", readonly=True)
    not_due = fields.Float("Not Due Yet", readonly=True)
    days_due_01to30 = fields.Float("1/30", readonly=True)
    days_due_31to60 = fields.Float("31/60", readonly=True)
    days_due_61to90 = fields.Float("61/90", readonly=True)
    days_due_91to120 = fields.Float("91/120", readonly=True)
    days_due_121togr = fields.Float("+121", readonly=True)
    invoice_ref = fields.Char("Their Invoice", size=25, readonly=True)
    invoice_id = fields.Many2one("account.invoice", "Invoice", readonly=True)
    salesman = fields.Many2one("res.users", "Sales Rep", readonly=True)

    @api.multi
    def execute_aging_query(self, age_date=False):
        if not age_date:
            age_date = fields.Date.context_today(self)

        query = """
            SELECT
                aml.id,
                aml.partner_id AS partner_id,
                ai.user_id AS salesman,
                aml.date AS date,
                aml.date AS date_due,
                ai.number AS invoice_ref,
                days_due AS avg_days_overdue,
                CASE
                    WHEN (days_due BETWEEN 1 AND 30) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual > 0) 
                            THEN -(aml.credit - (
                                SELECT coalesce(sum(apr.amount),0)	FROM account_partial_reconcile apr
                                WHERE	
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                                )
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL	AND aml.amount_residual < 0) 
                            THEN aml.debit - (
                                SELECT 	coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                WHERE
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN 
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS days_due_01to30,
                CASE
                    WHEN (days_due BETWEEN 31 AND 60) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual > 0) 
                            THEN -(aml.debit - (
                                SELECT coalesce(sum(apr.amount),0)	FROM account_partial_reconcile apr
                                WHERE	
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                                )
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL	AND aml.amount_residual < 0) 
                            THEN aml.credit - (
                                SELECT 	coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                WHERE
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN 
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS days_due_31to60,
                CASE
                    WHEN (days_due BETWEEN 61 AND 90) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual > 0) 
                            THEN -(aml.debit - (
                                SELECT coalesce(sum(apr.amount),0)	FROM account_partial_reconcile apr
                                WHERE	
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                                )
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL	AND aml.amount_residual < 0) 
                            THEN aml.credit - (
                                SELECT 	coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                WHERE
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN 
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS days_due_61to90,
                CASE
                    WHEN (days_due BETWEEN 91 AND 120) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual > 0) 
                            THEN -(aml.debit - (
                                SELECT coalesce(sum(apr.amount),0)	FROM account_partial_reconcile apr
                                WHERE	
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                                )
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL	AND aml.amount_residual < 0) 
                            THEN aml.credit - (
                                SELECT 	coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                WHERE
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN 
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS days_due_91to120,
                CASE
                    WHEN (days_due >= 121) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual > 0) 
                            THEN -(aml.debit - (
                                SELECT coalesce(sum(apr.amount),0)	FROM account_partial_reconcile apr
                                WHERE	
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                                )
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL	AND aml.amount_residual < 0) 
                            THEN aml.credit - (
                                SELECT 	coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                WHERE
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN 
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS days_due_121togr,
                CASE
                    WHEN (days_due < 1) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual > 0) 
                            THEN -(aml.debit - (
                                SELECT coalesce(sum(apr.amount),0)	FROM account_partial_reconcile apr
                                WHERE	
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                                )
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL	AND aml.amount_residual < 0) 
                            THEN aml.credit - (
                                SELECT 	coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                WHERE
                                    (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                                    AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN 
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS not_due,
                CASE
                    WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual > 0) 
                    THEN -(aml.debit - (
                        SELECT coalesce(sum(apr.amount),0)	FROM account_partial_reconcile apr
                        WHERE	
                            (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                            AND apr.max_date <= '%s')
                        )
                    WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                    WHEN (aml.full_reconcile_id IS NULL	AND aml.amount_residual < 0) 
                    THEN aml.credit - (
                        SELECT 	coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                        WHERE
                            (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id)
                            AND apr.max_date <= '%s')
                    WHEN (aml.full_reconcile_id IS NOT NULL) THEN 
                        CASE WHEN ai.type='in_invoice' THEN
                            aml.credit-(select
                            coalesce(sum(apr.amount),0) from account_partial_reconcile
                            apr where (apr.credit_move_id =aml.id or
                            apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                            WHEN ai.type = 'in_refund' THEN
                            aml.debit-(select
                            coalesce(sum(apr.amount),0) from account_partial_reconcile
                            apr where (apr.credit_move_id =aml.id or
                            apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                        END
                END AS total,
                CASE
                    WHEN days_due < 0 THEN 0
                    ELSE days_due 
                END AS "max_days_overdue",
                ai.id AS invoice_id,
                ai.date_due AS inv_date_due
            FROM
            account_move_line aml
            INNER JOIN
            (SELECT
                lt.id,
                CASE
                    WHEN inv.date_due IS NULL THEN 0
                    WHEN inv.id IS NOT NULL THEN '%s' - inv.date_due
                    ELSE current_date - lt.date 
                END AS days_due
            FROM
            account_move_line lt
            LEFT JOIN
            account_invoice inv
                ON lt.move_id = inv.move_id
            ) DaysDue
            ON DaysDue.id = aml.id
            INNER JOIN account_invoice AS ai ON ai.move_id = aml.move_id
            LEFT JOIN res_partner AS rp ON aml.partner_id = rp.id
            LEFT JOIN account_full_reconcile AS afr ON afr.id = aml.full_reconcile_id
            LEFT JOIN account_account_type atype on atype.id = aml.user_type_id
            WHERE
                atype.type = 'payable'
                AND aml.date <= '%s'
                AND ai.state IN ('open', 'paid')
            GROUP BY
                aml.partner_id,aml.id,ai.number,days_due,ai.user_id,ai.id,ai.warehouse_id,rp.prop_mgmt_id,rp.partner_type,afr.create_date,afr.name
        UNION
            SELECT
                aml.id,
                aml.partner_id AS partner_id,
                ai.user_id AS salesman,
                aml.date AS date,
                aml.date AS date_due,
                ai.number AS invoice_ref,
                days_due AS avg_days_overdue,
                CASE
                    WHEN (days_due days_due BETWEEN 1 AND 30) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL
                            AND aml.amount_residual > 0) THEN -(aml.debit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                            WHERE
                                (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s'))
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual < 0) 
                                THEN aml.credit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                    WHERE (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS days_due_01to30,
                CASE
                    WHEN (days_due days_due BETWEEN 31 AND 60) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL
                            AND aml.amount_residual > 0) THEN -(aml.debit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                            WHERE
                                (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s'))
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual < 0) 
                                THEN aml.credit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                    WHERE (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS days_due_31to60,
                CASE
                    WHEN (days_due BETWEEN 61 AND 90) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL
                            AND aml.amount_residual > 0) THEN -(aml.debit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                            WHERE
                                (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s'))
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual < 0) 
                                THEN aml.credit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                    WHERE (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS days_due_61to90,
                CASE
                    WHEN (days_due BETWEEN 91 AND 120) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL
                            AND aml.amount_residual > 0) THEN -(aml.debit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                            WHERE
                                (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s'))
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual < 0) 
                                THEN aml.credit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                    WHERE (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS days_due_91to120,
                CASE
                    WHEN (days_due >=121) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL
                            AND aml.amount_residual > 0) THEN -(aml.debit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                            WHERE
                                (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s'))
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual < 0) 
                                THEN aml.credit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                    WHERE (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS days_due_121togr,
                CASE
                    WHEN (days_due < 1) THEN 
                        CASE
                            WHEN (aml.full_reconcile_id IS NULL
                            AND aml.amount_residual > 0) THEN -(aml.debit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                            WHERE
                                (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s'))
                            WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                            WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual < 0) 
                                THEN aml.creit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                                    WHERE (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s')
                            WHEN (aml.full_reconcile_id IS NOT NULL) THEN
                                CASE WHEN ai.type='in_invoice' THEN
                                    aml.credit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                    WHEN ai.type = 'in_refund' THEN
                                    aml.debit-(select
                                    coalesce(sum(apr.amount),0) from account_partial_reconcile
                                    apr where (apr.credit_move_id =aml.id or
                                    apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                                END
                        END
                    ELSE 0 
                END AS not_due,
                CASE
                    WHEN (aml.full_reconcile_id IS NULL
                    AND aml.amount_residual > 0) THEN -(aml.debit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                    WHERE
                        (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s'))
                    WHEN (aml.full_reconcile_id is NULL and aml.amount_residual=0) THEN 0
                    WHEN (aml.full_reconcile_id IS NULL AND aml.amount_residual < 0) 
                        THEN aml.credit - (SELECT coalesce(sum(apr.amount),0) FROM account_partial_reconcile apr
                            WHERE (apr.credit_move_id = aml.id OR apr.debit_move_id = aml.id) AND apr.max_date <= '%s')
                    WHEN (aml.full_reconcile_id IS NOT NULL) THEN
                        CASE WHEN ai.type='in_invoice' THEN
                            aml.credit-(select
                            coalesce(sum(apr.amount),0) from account_partial_reconcile
                            apr where (apr.credit_move_id =aml.id or
                            apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                            WHEN ai.type = 'in_refund' THEN
                            aml.debit-(select
                            coalesce(sum(apr.amount),0) from account_partial_reconcile
                            apr where (apr.credit_move_id =aml.id or
                            apr.debit_move_id=aml.id) and apr.max_date <= '%s')
                        END
                END AS total,
                CASE
                    WHEN days_due < 0 THEN 0
                    ELSE days_due 
                END AS "max_days_overdue",
                ai.id AS invoice_id,
                ai.date_due AS inv_date_due
            FROM
                account_move_line aml
            INNER JOIN
                (SELECT
                    lt.id,
                    CASE
                        WHEN inv.date_due IS NULL THEN 0
                        WHEN inv.id IS NOT NULL THEN '%s' - inv.date_due
                        ELSE current_date - lt.date 
                    END AS days_due
                    FROM
                        account_move_line lt
                    LEFT JOIN account_invoice inv ON lt.move_id = inv.move_id
                ) DaysDue ON DaysDue.id = aml.id
            LEFT JOIN account_invoice AS ai ON ai.move_id = aml.move_id
            LEFT JOIN res_partner AS rp ON aml.partner_id = rp.id
            LEFT JOIN account_full_reconcile AS afr ON afr.id = aml.full_reconcile_id
            LEFT JOIN account_account_type atype on atype.id = aml.user_type_id
            WHERE
                atype.type = 'payable' AND
                aml.date <= '%s' AND
                aml.partner_id IS NOT NULL
            GROUP BY
                aml.partner_id,aml.id,ai.number,days_due,ai.user_id,ai.id,ai.warehouse_id,rp.prop_mgmt_id,rp.partner_type,afr.create_date,afr.name
        UNION
            SELECT
                aml.id,
                aml.partner_id AS partner_id,
                aml.create_uid AS salesman,
                aml.date AS date,
                aml.date AS date_due,
                ' ' AS invoice_ref,
                0 AS avg_days_overdue,
                0 AS days_due_01to30,
                0 AS days_due_31to60,
                0 AS days_due_61to90,
                0 AS days_due_91to120,
                0 AS days_due_121togr,
                0 AS max_days_overdue,
                0 AS not_due,
                CASE
                WHEN (aml.debit - (SELECT sum(l.credit) FROM account_move_line l WHERE l.full_reconcile_id = aml.full_reconcile_id 	AND l.date <='%s')) > 0 
                THEN -(aml.debit - (SELECT sum(l.credit) FROM 	account_move_line l WHERE l.full_reconcile_id = aml.full_reconcile_id AND l.date <= '%s'))
                ELSE 0 END AS total,
                NULL AS invoice_id,
                aml.date AS inv_date_due
            FROM
                account_move_line aml
            LEFT JOIN account_account_type at on at.id = aml.user_type_id
            LEFT JOIN account_invoice AS ai ON ai.move_id = aml.move_id
            LEFT JOIN account_full_reconcile AS afr ON afr.id = aml.full_reconcile_id
            WHERE
                aml.date <= '%s' AND
                at.type = 'payable' AND 
                aml.debit > 0
            GROUP BY
                ai.warehouse_id, aml.partner_id,aml.create_uid,aml.id,afr.create_date,afr.name
        """ % (
            age_date,age_date,age_date,age_date,age_date,age_date,age_date,
            age_date,age_date,age_date,age_date,age_date,age_date,age_date,
            age_date,age_date,age_date,age_date,age_date,age_date,age_date,
            age_date,age_date,age_date,age_date,age_date,age_date,age_date,
            age_date,age_date,age_date,age_date,age_date,age_date,age_date,
            age_date,age_date,age_date,age_date,age_date,age_date,age_date,
            age_date,age_date,age_date,age_date,age_date,age_date,age_date,
            age_date,age_date,age_date,age_date,age_date,age_date,age_date,
            age_date,age_date,age_date,age_date,age_date,age_date,age_date,
        )

        tools.drop_view_if_exists(self.env.cr, self._table)
        # pylint: disable=sql-injection
        q = """CREATE OR REPLACE VIEW %s AS (%s)""" % (self._table, (query))
        self.env.cr.execute(q)

    @api.multi
    def open_document(self):
        """
            @description  Open form view of Supplier Invoice
        """
        action = self.env.ref("account.action_invoice_tree2").read()[0]
        action["views"] = [(self.env.ref("account.invoice_supplier_form").id, "form")]
        action["res_id"] = self.invoice_id.id
        return action

    @api.model_cr
    def init(self):
        self.execute_aging_query()
        super(ResPartnerAgingSupplier, self).init()
