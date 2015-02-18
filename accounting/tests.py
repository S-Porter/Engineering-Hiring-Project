#!/user/bin/env python2.7

import unittest
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy
from tools import PolicyAccounting

"""
#######################################################
Test Suite for PolicyAccounting
#######################################################
"""


class TestBillingSchedules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        db.session.add(cls.policy)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        pass

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.commit()

    def test_annual_billing_schedule(self):
        self.policy.billing_schedule = "Annual"
        # No invoices currently exist
        self.assertFalse(self.policy.invoices)
        # 1 invoice should be made when this is initiated
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 1)
        self.assertEquals(self.policy.invoices[0].amount_due,
                          self.policy.annual_premium)

    def test_twopay_billing_schedule(self):
        self.policy.billing_schedule = "Two-Pay"
        # No invoices currently exist
        self.assertFalse(self.policy.invoices)
        # 2 invoices should be made when this is initiated
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 2)
        self.assertEquals(self.policy.invoices[0].amount_due,
                          self.policy.annual_premium / 2)

    def test_quarterly_billing_schedule(self):
        self.policy.billing_schedule = "Quarterly"
        # No invoices currently exist
        self.assertFalse(self.policy.invoices)
        # 4 invoices should be made when this is initiated
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 4)
        self.assertEquals(self.policy.invoices[0].amount_due,
                          self.policy.annual_premium / 4)

    def test_monthly_billing_schedule(self):
        self.policy.billing_schedule = "Monthly"
        # No invoices currently exist
        self.assertFalse(self.policy.invoices)
        # 12 invoices should be made when this is initiated
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 12)
        self.assertEquals(self.policy.invoices[0].amount_due,
                          self.policy.annual_premium / 12)


class TestReturnAccountBalance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_annual_on_eff_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 1200)

    def test_quarterly_on_eff_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 300)

    def test_quarterly_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[3].bill_date), 1200)

    def test_quarterly_on_second_installment_bill_date_with_full_payment(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.payments.append(pa.make_payment(amount=600, contact_id=self.policy.named_insured,
                                             date_cursor=invoices[1].bill_date))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), 0)


class TestCancellations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_cancellation_pending_on_due_date(self):
        pa = PolicyAccounting(self.policy.id)
        self.assertFalse(pa.evaluate_cancellation_pending_due_to_non_pay(date(2015, 2, 1)))

    def test_cancellation_pending_after_due_date(self):
        pa = PolicyAccounting(self.policy.id)
        self.assertTrue(pa.evaluate_cancellation_pending_due_to_non_pay(date(2015, 2, 2)))

    def test_cancellation_pending_day_before_cancel_date(self):
        pa = PolicyAccounting(self.policy.id)
        self.assertTrue(pa.evaluate_cancellation_pending_due_to_non_pay(date(2015, 2, 14)))

    def test_cancellation_pending_on_cancel_date(self):
        pa = PolicyAccounting(self.policy.id)
        self.assertFalse(pa.evaluate_cancellation_pending_due_to_non_pay(date(2015, 2, 15)))

    def test_payment_in_cancellation_pending_by_insured(self):
        self.policy.billing_schedule = 'Monthly'
        pa = PolicyAccounting(self.policy.id)
        self.assertFalse(pa.make_payment(100, self.policy.named_insured, date(2015, 2, 7)))

    def test_payment_in_cancellation_pending_by_agent(self):
        self.policy.billing_schedule = 'Monthly'
        pa = PolicyAccounting(self.policy.id)
        self.payments.append(pa.make_payment(100, self.policy.agent, date(2015, 2, 7)))
        # balance should be 100. by the time invoice 1 is pending cancellation, invoice 2
        # is already due (this only applies to monthly billing).
        self.assertEquals(pa.return_account_balance(date(2015, 2, 7)), 100)

    def test_policy_cancellation(self):
        pa = PolicyAccounting(self.policy.id)
        pa.cancel_policy('testing reasons')
        self.assertEquals(self.policy.status, 'Canceled')
        self.assertNotEquals(self.policy.cancel_reason, '')

    def test_policy_cancellation_on_already_canceled(self):
        pa = PolicyAccounting(self.policy.id)
        pa.cancel_policy('testing reasons')
        self.assertFalse(pa.cancel_policy('more testing reasons'))


class TestChangedBillingCycles(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_change_billing_cycle_annual_to_two_pay(self):
        self.policy.billing_schedule = 'Annual'
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date(2015, 1, 2)), 1200)
        pa.change_billing_schedule('Two-Pay')
        self.assertEquals(pa.return_account_balance(date(2015, 1, 2)), 600)

    def test_change_billing_cycle_two_pay_to_quarterly(self):
        self.policy.billing_schedule = 'Two-Pay'
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date(2015, 1, 2)), 600)
        pa.change_billing_schedule('Quarterly')
        self.assertEquals(pa.return_account_balance(date(2015, 1, 2)), 300)

    def test_change_billing_cycle_quarterly_to_monthly(self):
        self.policy.billing_schedule = 'Quarterly'
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date(2015, 1, 2)), 300)
        pa.change_billing_schedule('Monthly')
        self.assertEquals(pa.return_account_balance(date(2015, 1, 2)), 100)


class TestMiscFunctions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_make_payment(self):
        self.policy.billing_schedule = 'Monthly'
        pa = PolicyAccounting(self.policy.id)
        self.payments.append(pa.make_payment(100, self.policy.named_insured, date(2015, 1, 10)))
        self.assertEquals(pa.return_account_balance(date(2015, 1, 10)), 0)
