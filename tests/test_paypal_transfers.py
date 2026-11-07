import unittest
from decimal import Decimal
from unittest.mock import patch
from datetime import datetime
import stripe
import main
import test_monthly_fees


def balance(amount=900, fee=78, kind='payment', paypal=True):
    return {
        'id': 'txn_test', 'object': 'balance_transaction', 'amount': amount,
        'fee': fee, 'net': amount-fee, 'currency': 'eur', 'type': kind,
        'source': 'py_test', 'created': 1786233600, 'available_on': 1786406400,
        'description': 'Original payment',
        'fee_details': ([{'amount': 66, 'type': 'payment_method_passthrough_fee', 'description': 'PayPal fees', 'currency': 'eur'},
                         {'amount': 12, 'type': 'stripe_fee', 'description': 'Stripe processing fees', 'currency': 'eur'}] if paypal else []),
    }


class PayPalTransferTest(unittest.TestCase):
    def test_real_fee_structure(self):
        self.assertEqual(main.split_paypal_transfer(balance()), (834, 12, True))

    def test_other_payments_and_refunds_unchanged(self):
        self.assertEqual(main.split_paypal_transfer(balance(paypal=False)), (900, 78, False))
        self.assertEqual(main.split_paypal_transfer(balance(amount=-900, fee=0, kind='payment_refund')), (-900, 0, False))
        self.assertEqual(main.split_paypal_transfer(balance(amount=0)), (0, 78, False))

    def test_inconsistent_details_stop_export(self):
        with self.assertRaises(ValueError):
            main.split_paypal_transfer(balance(fee=80))
        data = balance()
        data['fee_details'][0]['currency'] = 'usd'
        with self.assertRaises(ValueError):
            main.split_paypal_transfer(data)

    def test_full_api_to_csv_in_both_fee_modes(self):
        tx = stripe.BalanceTransaction.construct_from(balance(), None)
        with patch.object(stripe.BalanceTransaction, 'list') as query:
            query.return_value.auto_paging_iter.return_value = iter([tx])
            rows = main.fetch_balance_transactions(datetime(2026,8,1), datetime(2026,8,31))
        for aggregate in (True, False):
            with self.subTest(aggregate=aggregate):
                exported = test_monthly_fees.MonthlyFeesTest().export(rows, aggregate)
                self.assertEqual(len(exported), 2)
                self.assertEqual(Decimal(exported[0]['Betrag']), Decimal('8.34'))
                self.assertEqual(exported[0]['Auftraggeber / Empfänger'], 'PayPal')
                self.assertIn('Geldtransit von PayPal', exported[0]['Verwendungszweck'])
                self.assertEqual(Decimal(exported[1]['Betrag']), Decimal('-0.12'))
                self.assertEqual(sum(Decimal(r['Betrag']) for r in exported), Decimal('8.22'))
