import unittest
from unittest.mock import patch
import stripe
import main


class CustomerNamesTest(unittest.TestCase):
    def charge(self, **fields):
        return stripe.Charge.construct_from(fields, None)

    def test_paypal_charge_prefixes(self):
        for prefix in ('py_', 'ch_'):
            with self.subTest(prefix=prefix), patch.object(stripe.Charge, 'retrieve', return_value=self.charge(
                billing_details=None, payment_method_details={'paypal': {'payer_name': 'PayPal Kunde'}}
            )), patch.object(stripe.PaymentMethod, 'retrieve') as wrong_endpoint:
                self.assertEqual(main.getCustomerByPayment(prefix+'test'), 'PayPal Kunde')
                wrong_endpoint.assert_not_called()

    def test_billing_name_preferred(self):
        with patch.object(stripe.Charge, 'retrieve', return_value=self.charge(
            billing_details={'name': 'Rechnungskunde'},
            payment_method_details={'paypal': {'payer_name': 'PayPal Kunde'}}
        )):
            self.assertEqual(main.getCustomerByPayment('ch_test'), 'Rechnungskunde')

    def test_customer_fallback(self):
        with patch.object(stripe.Charge, 'retrieve', return_value=self.charge(
            customer='cus_test', payment_method_details={'paypal': {}}
        )), patch.object(stripe.Customer, 'retrieve', return_value=stripe.Customer.construct_from({'name': 'Stripe Kunde'}, None)):
            self.assertEqual(main.getCustomerByPayment('py_test'), 'Stripe Kunde')

    def test_payment_intent_latest_charge(self):
        with patch.object(stripe.PaymentIntent, 'retrieve', return_value=stripe.PaymentIntent.construct_from({'latest_charge': 'py_test'}, None)), patch.object(stripe.Charge, 'retrieve', return_value=self.charge(payment_method_details={'paypal': {'payer_name': 'PayPal Kunde'}})):
            self.assertEqual(main.getCustomerByPayment('pi_test'), 'PayPal Kunde')

    def test_missing_name(self):
        with patch.object(stripe.Charge, 'retrieve', return_value=self.charge(billing_details=None, payment_method_details=None)):
            self.assertEqual(main.getCustomerByPayment('py_test'), main.STRIPE_NAME)


if __name__ == '__main__':
    unittest.main()
