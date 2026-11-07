import contextlib
import csv
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import main


def transaction(kind, date, amount='10,00', fee='0,00'):
    return ['txn_test', kind, '', amount, fee, '', '', '', '', date, date, 'Test']


class MonthlyFeesTest(unittest.TestCase):
    def export(self, rows, aggregate):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'export.csv'
            with patch('sys.argv', ['main.py']), patch.object(main, 'STRIPE_METHOD', 'CSV'), patch.object(main, 'SUM_FEES', aggregate), patch.object(main, 'get_transactions_data', return_value=rows), patch.object(main, 'generate_export_filename', return_value=str(output)), patch.object(main, 'getCustomerByPayment', return_value='Testkunde'), patch.object(main, 'createDefaultDescription', return_value='Testgebühr'), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                main.main()
            with output.open(newline='', encoding='utf-8') as handle:
                return list(csv.DictReader(handle, delimiter=';'))

    def test_month_and_category_separation_in_reverse_order(self):
        rows = [
            transaction('charge', '2027-01-20 12:00:00', fee='0,20'),
            transaction('charge', '2026-12-20 12:00:00', fee='0,10'),
            transaction('charge', '2027-01-02 12:00:00', fee='0,10'),
            transaction('payment', '2027-01-03 12:00:00', fee='0,40'),
            transaction('payment', '2026-12-03 12:00:00', fee='0,50'),
            transaction('stripe_fee', '2027-01-04 12:00:00', amount='-0,60'),
            transaction('stripe_fee', '2026-12-04 12:00:00', amount='-0,70'),
        ]
        exported = self.export(rows, True)
        fees = [r for r in exported if r['Auftraggeber / Empfänger'] == main.STRIPE_NAME]
        self.assertEqual(len(fees), 6)
        self.assertEqual([r['Betrag'] for r in fees], ['-0.1', '-0.5', '-0.7', '-0.3', '-0.4', '-0.6'])
        self.assertEqual(fees[3]['Buchungsdatum'], '2027-01-31 00:00:00')
        for row in fees:
            self.assertIn(row['Buchungsdatum'][:7], row['Verwendungszweck'])
            self.assertEqual(row['Wertstellungsdatum'], row['Buchungsdatum'][:7] + '-31 00:00:00')
            self.assertEqual(float(row['Betrag']), -float(row['Soll Betrag (Ausgabe)']))
        self.assertEqual(len(exported), 11)

    def test_individual_fees_unchanged(self):
        exported = self.export([
            transaction('charge', '2026-12-20 12:00:00', fee='0,10'),
            transaction('stripe_fee', '2027-01-04 12:00:00', amount='-0,60'),
        ], False)
        self.assertEqual(len(exported), 3)
        self.assertEqual(exported[1]['Betrag'], '-0.1')
        self.assertTrue(exported[1]['Verwendungszweck'].startswith('Fees for payment'))
        self.assertEqual(exported[2]['Betrag'], '-0.6')

    def test_empty_export(self):
        self.assertEqual(self.export([], True), [])

    def test_zero_fees_produce_no_summary(self):
        exported = self.export([transaction('charge', '2026-12-20 12:00:00')], True)
        self.assertEqual(len(exported), 1)

    def test_month_end_including_leap_year_and_cross_month_settlement(self):
        for booking_date, expected in [
            ('2026-02-03 14:20:00', '2026-02-28 00:00:00'),
            ('2028-02-03 14:20:00', '2028-02-29 00:00:00'),
            ('2026-04-03 14:20:00', '2026-04-30 00:00:00'),
        ]:
            with self.subTest(booking_date=booking_date):
                rows = [transaction('charge', booking_date, fee='0,10'),
                        transaction('payment', booking_date, fee='0,20'),
                        transaction('stripe_fee', booking_date, amount='-0,30')]
                for row in rows:
                    row[10] = '2028-03-01 00:00:00'
                exported = self.export(rows, True)
                fees = [r for r in exported if r['Auftraggeber / Empfänger'] == main.STRIPE_NAME]
                self.assertEqual(len(fees), 3)
                for fee in fees:
                    self.assertEqual(fee['Wertstellungsdatum'], expected)
                    self.assertEqual(fee['Buchungsdatum'], expected)
