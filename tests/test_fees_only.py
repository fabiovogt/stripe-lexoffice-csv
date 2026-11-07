import unittest
import test_monthly_fees as fixtures


class FeesOnlyTest(unittest.TestCase):
    def test_only_fee_rows_with_both_aggregation_settings(self):
        rows = [
            fixtures.transaction('charge', '2026-10-04 00:00:00', fee='0,30'),
            fixtures.transaction('payment', '2026-10-05 00:00:00', fee='0,20'),
            fixtures.transaction('stripe_fee', '2026-10-06 00:00:00', amount='-0,10'),
            fixtures.transaction('payout', '2026-10-07 00:00:00', amount='-20,00'),
            fixtures.transaction('payment_refund', '2026-10-08 00:00:00', amount='-4,85'),
        ]
        for aggregate in (True, False):
            with self.subTest(aggregate=aggregate):
                result = fixtures.MonthlyFeesTest().export(rows, aggregate, fees_only=True)
                self.assertEqual(len(result), 2 if aggregate else 3)
                self.assertAlmostEqual(sum(float(r['Betrag']) for r in result), -0.60)
                self.assertTrue(all(r['Auftraggeber / Empfänger'] == __import__('main').STRIPE_NAME for r in result))
                if aggregate:
                    self.assertEqual(result[0]['Verwendungszweck'], 'Stripe Processing Fees (2026-10)')
                    self.assertEqual(result[0]['Buchungsdatum'], '2026-10-31 00:00:00')

    def test_no_fees_writes_header_only(self):
        result = fixtures.MonthlyFeesTest().export([
            fixtures.transaction('payment', '2026-10-05 00:00:00')
        ], True, fees_only=True)
        self.assertEqual(result, [])
