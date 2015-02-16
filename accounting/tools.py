#!/user/bin/env python2.7

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import and_

from accounting import db
from models import Contact, Invoice, Payment, Policy

import logging
logging.basicConfig(level=logging.DEBUG)

"""
#######################################################
This is the base code for the intern project.

If you have any questions, please contact Amanda at:
    amanda@britecore.com
#######################################################
"""


class PolicyAccounting(object):
    """
     Each policy has its own instance of accounting.
    """
    def __init__(self, policy_id):
        """
         Creates a new object tied to a specific policy id. Checks if any
         invoices have been created and initializes them if necessary. Also
         allows the user to create a new policy from the console if they
         attempted to use a policy ID that didn't exist.
        """
        self.policy = Policy.query.filter_by(id=policy_id)

        if self.policy.count() == 0:
            raw = raw_input('Policy not found, do you want to'
                            + 'create a new policy? (yes/no): ')
            answer = raw.lower().strip()
            if answer in ['yes', 'y']:
                details = self.get_policy_details_from_console()
                self.policy = PolicyAccounting.create_new_policy(details['policy_name'], details['billing'],
                                                                 details['insured'], details['agent'],
                                                                 details['premium'], details['eff_date'])
            else:
                return
        elif self.policy.count() > 1:
            logging.warning('Found more than 1 policy with that ID, exiting.')
            return
        else:
            self.policy = self.policy.first()

        if not self.policy.invoices:
            logging.info('No invoices found for policy ' + str(policy_id))
            self.make_invoices()

    @staticmethod
    def create_new_policy(policy_number, billing_type, named_insured,
                          agent_name, annual_premium, effective_date=None):
        """
         Factory method that creates a new policy and commits it to the db.
         Returns a PolicyAccounting object for the created policy.
        """
        if not effective_date:
            effective_date = datetime.now().date()

        logging.info('Creating new policy')
        new_policy = Policy(policy_number, effective_date, annual_premium)
        new_policy.billing_schedule = billing_type

        agent_query = Contact.query.filter_by(name=agent_name)\
                                   .filter(Contact.role == 'Agent')
        if agent_query.count() == 0:
            logging.info('Given agent name not found, adding new agent to db.')
            agent = Contact(agent_name, 'Agent')
            db.session.add(agent)
            db.session.commit()
        elif agent_query.count() > 1:
            logging.info('Found more than 1 agent with the '
                         + 'same name, picking the first.')
            agent = agent_query.first()
        else:
            agent = agent_query.first()

        new_policy.agent = agent.id

        insured_query = Contact.query.filter_by(name=named_insured)\
                                     .filter(Contact.role == 'Named Insured')
        if insured_query.count() == 0:
            logging.info('Given named-insured was not found, adding to db.')
            insured = Contact(named_insured, 'Named Insured')
            db.session.add(insured)
            db.session.commit()
        elif insured_query.count() > 1:
            logging.info('Found more than 1 insured with the '
                         + 'same name, picking the first.')
            insured = insured_query.first()
        else:
            insured = insured_query.first()

        new_policy.named_insured = insured.id
        db.session.add(new_policy)
        db.session.commit()

        return PolicyAccounting(new_policy.id)

    def get_policy_details_from_console(self):
        """
         Prompts the user for policy details and returns a dict with all
         the info required to make a policy.
        """
        policy_info = {}

        raw = raw_input('Please enter the policy number: ')
        policy_info['policy_name'] = str.title(raw.strip())

        raw = raw_input('Please enter effective date as yyyy-mm-dd, or '
                        + 'leave it blank and hit enter for today: ')
        if not raw.strip():
            policy_info['eff_date'] = datetime.now().date()
        else:
            policy_info['eff_date'] = datetime.strptime(raw.strip(), '%Y-%m-%d')

        raw = raw_input('Please enter a billing frequency: ')
        while str.title(raw.strip()) not in ['Annual', 'Two-Pay', 'Quarterly', 'Monthly']:
            raw = raw_input('Billing options are Annual, Two-Pay, Quarterly, and Monthly: ')
        policy_info['billing'] = str.title(raw.strip())

        raw = raw_input('Please enter the named-insured, '
                        + 'exactly as it should appear: ')
        policy_info['insured'] = str.title(raw.strip())

        raw = raw_input("Please enter the agent's name: ")
        policy_info['agent'] = str.title(raw.strip())

        raw = raw_input("Please enter the yearly premium as a whole number: ")
        policy_info['premium'] = raw.strip()

        return policy_info

    def return_account_balance(self, date_cursor=None):
        """
         Returns the remaining account balance on a specified date. Defaults
         to today's date if nothing is specified.
        """
        if not date_cursor:
            date_cursor = datetime.now().date()

        logging.debug("Finding balance for " + str(date_cursor))
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()
        due_now = 0
        for invoice in invoices:
            due_now += invoice.amount_due

        logging.debug('Total due, not counting payments: $' + str(due_now))
        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()

        for payment in payments:
            logging.debug('Payment found - $' + str(payment.amount_paid))
            due_now -= payment.amount_paid

        logging.info('Account balance: ' + str(due_now))
        return due_now

    def make_payment(self, amount=0, contact_id=None, date_cursor=None):
        """
         Adds a new payment to the account with the given information.
        """

        if not date_cursor:
            date_cursor = datetime.now().date()
        logging.debug('Making payment for date ' + str(date_cursor))

        if not contact_id:
            if self.policy.named_insured:
                logging.debug("No contact_id given, using the policy's named_insured.")
                contact_id = self.policy.named_insured
            elif self.policy.agent:
                logging.debug("No contact_id given and no named-insured"
                              + " on the policy, using the policy's agent.")
                contact_id = self.policy.agent
            else:
                logging.debug("No contact_id, named-insured, or agent could be found. Exiting.")
                return

        contact = Contact.query.filter_by(id=contact_id).one()
        if contact.role != 'Agent' and self.evaluate_cancellation_pending_due_to_non_pay(date_cursor):
            print "Cancellation pending, please contact your agent to make a payment."
            return False

        payment = Payment(self.policy.id,
                          contact_id,
                          amount,
                          date_cursor)
        logging.debug("Payment created, adding to db.")
        db.session.add(payment)
        db.session.commit()
        logging.debug("Payment committed.")

        return payment

    def update_named_insured(self, new_insured):
        """
         Updates the policyholder for the current account.
         Returns the id of the new named-insured.
        """
        logging.info('Updating named-insured for policy id ' + str(self.policy.id))
        contact_query = Contact.query.filter_by(name=new_insured)\
                                     .filter(Contact.role == 'Named Insured')
        if contact_query.count() == 0:
            logging.info('No current contact with this name, '
                         + 'creating new contact.')
            insured = Contact(new_insured, 'Named Insured')
            db.session.add(insured)
            db.session.commit()
        else:
            logging.info('Named-insured already in the system, '
                         + 'keeping existing id.')
            insured = contact_query.first()

        self.policy.named_insured = insured.id
        db.session.commit()
        return self.policy.named_insured

    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        """
         If this function returns true, an invoice on a policy has
         passed the due date without being paid in full. However,
         it has not necessarily made it to the cancel_date yet.
        """
        if not date_cursor:
            date_cursor = datetime.now().date()
        logging.info("Checking pending cancel for " + str(date_cursor))

        invoice = Invoice.query.filter_by(policy_id=self.policy.id)\
                               .filter(and_(Invoice.due_date < date_cursor,
                                            Invoice.cancel_date > date_cursor))\
                               .first()
        if not invoice:
            logging.info('Not in pending time period.')
            return False
        elif self.return_account_balance(date_cursor):
            logging.info('In pending time period, balance due. Pending cancellation.')
            return True
        else:
            logging.info('In pending time period, account is current.')
            return False

    def evaluate_cancel(self, date_cursor=None):
        """
         Determines whether the policy should have been cancelled on the
         given date(or today, if the date was not given).
        """
        if not date_cursor:
            logging.debug("No date passed, evaluating at the current date.")
            date_cursor = datetime.now().date()

        logging.debug("Querying invoices...")
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.cancel_date <= date_cursor)\
                                .order_by(Invoice.bill_date)\
                                .all()
        logging.debug(str(len(invoices)) + " invoices found...")

        for invoice in invoices:
            if not self.return_account_balance(invoice.cancel_date):
                logging.debug("Balance on invoice cancel date: "
                              + str(self.return_account_balance(invoice.cancel_date)))
                continue
            else:
                print "THIS POLICY SHOULD HAVE CANCELED"
                break
        else:
            print "THIS POLICY SHOULD NOT CANCEL"

    def make_invoices(self):
        """
         Deletes and recreates all invoices for the year,
         starting at the policy effective_date.
        """
        logging.debug('Deleting any invoices for ' + self.policy.policy_number)
        for invoice in self.policy.invoices:
            db.session.delete(invoice)

        billing_schedules = {'Annual': None, 'Two-Pay': 2, 'Quarterly': 4, 'Monthly': 12}

        logging.debug('Creating invoices...')
        invoices = []
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date,  # bill_date
                                self.policy.effective_date + relativedelta(months=1),  # due
                                self.policy.effective_date + relativedelta(months=1, days=14),  # cancel
                                self.policy.annual_premium)
        invoices.append(first_invoice)

        if self.policy.billing_schedule == "Annual":
            logging.info('Annual billing created for ' + self.policy.policy_number)
            pass
        elif self.policy.billing_schedule == "Two-Pay":
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                months_after_eff_date = i*6
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
            logging.info('Two-Pay billing created for ' + self.policy.policy_number)
        elif self.policy.billing_schedule == "Quarterly":
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                months_after_eff_date = i*3
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
            logging.info('Quarterly billing created for ' + self.policy.policy_number)
        elif self.policy.billing_schedule == "Monthly":
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                months_after_eff_date = i
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
            logging.info('Monthly billing created for ' + self.policy.policy_number)
        else:
            logging.warning('No invoices created, ' + self.policy.policy_number + ' had an invalid billing type.')
            print "You have chosen a bad billing schedule."

        for invoice in invoices:
            db.session.add(invoice)
        logging.debug('Begin db commit for invoices on ' + self.policy.policy_number)
        db.session.commit()
        logging.debug('End db commit')

################################
# The functions below are for the db and
# shouldn't need to be edited.
################################


def build_or_refresh_db():
    db.drop_all()
    db.create_all()
    insert_data()
    print "DB Ready!"


def insert_data():
    # Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.agent = bob_smith.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()

    PolicyAccounting.create_new_policy('Policy Four', 'Two-Pay', 'Ryan Bucket',
                                       'John Doe', 500,
                                       datetime.strptime('2015-02-01', '%Y-%m-%d'))

    pa = PolicyAccounting(1)
    pa.update_named_insured('John Doe')
    pa.make_payment(365)
