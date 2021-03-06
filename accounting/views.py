# You will probably need more methods from flask but this one is a good start.
from flask import render_template, redirect, request, flash, url_for, jsonify
from datetime import date, datetime
from decimal import Decimal, ROUND_05UP
from sqlalchemy import and_

# Import things from Flask that we need.
from accounting import app, db

# Import our models
from models import Payment, Contact, Invoice, Policy
from tools import PolicyAccounting

app.secret_key = 'super secret'


# Routing for the server.
@app.route('/')
@app.route('/index/')
def index():
    msg = "Please enter a policy ID and date to view more information on an "\
          + "account. If the date is left blank, it will default to today."
    return render_template('index.html', name='Mr. Tester', text=msg)


@app.route('/policy/', methods=['POST'])
def policy():
    cents = Decimal('.01')

    if not request.form['date']:
        date_cursor = datetime.now().date()
    else:
        try:
            date_cursor = datetime.strptime(request.form['date'], '%Y-%m-%d')
            date_cursor = date_cursor.date()
        except:
            date_cursor = datetime.now().date()
            flash("Entered date was not valid, showing information for today's date.")

    policies = Policy.query.filter_by(id=request.form['id']).all()
    if not policies:
        flash("Entered policy id not found, please try a different policy ID.")
        return redirect(url_for('index'))

    current = policies[0]
    pa = PolicyAccounting(current.id)
    balance = pa.return_account_balance(date_cursor)
    current_invoices = Invoice.query.filter_by(policy_id=request.form['id'])\
                                    .filter(and_(Invoice.deleted == 0, Invoice.bill_date <= date_cursor))\
                                    .all()
    deleted_invoices = Invoice.query.filter_by(policy_id=request.form['id'])\
                                    .filter(and_(Invoice.deleted == 1, Invoice.bill_date <= date_cursor))\
                                    .all()
    payments = Payment.query.filter_by(policy_id=request.form['id']).all()

    # map ids to names, and currency to strings for use in the template
    for payment in payments:
        contact = Contact.query.filter_by(id=payment.contact_id).one()
        payment.contact_name = contact.name
        payment.amount_text = str(Decimal(payment.amount_paid).quantize(cents, ROUND_05UP))
    for invoice in current_invoices:
        invoice.amount_text = str(Decimal(invoice.amount_due).quantize(cents, ROUND_05UP))
    for invoice in deleted_invoices:
        invoice.amount_text = str(Decimal(invoice.amount_due).quantize(cents, ROUND_05UP))

    insured = Contact.query.filter_by(id=current.named_insured).one()
    agent = Contact.query.filter_by(id=current.agent).one()

    data = {'policy_id': request.form['id'],
            'date': str(date_cursor),
            'balance': balance,
            'current_invoices': current_invoices,
            'deleted_invoices': deleted_invoices,
            'payments': payments,
            'policy_name': current.policy_number,
            'billing': current.billing_schedule,
            'effective_date': current.effective_date,
            'status': current.status,
            'annual_premium': Decimal(current.annual_premium).quantize(cents, ROUND_05UP),
            'named_insured': insured.name,
            'agent_name': agent.name,
            'canceled_date': current.canceled_date,
            'cancel_reason': current.cancel_reason}

    return render_template('policy.html', passed_data=data)


@app.route('/maintenance/', methods=['POST'])
def maintenance():
    policy = Policy.query.filter_by(id=request.form['id']).one()
    insured = Contact.query.filter_by(id=policy.named_insured).one()
    agent = Contact.query.filter_by(id=policy.agent).one()
    current_billing = policy.billing_schedule

    # returns a list of all schedules without the current included
    # simplifies the clientside checking
    available_schedules = []
    for schedule in PolicyAccounting.billing_schedules:
        if schedule != current_billing:
            available_schedules.append(schedule)

    data = {'policy_id': request.form['id'],
            'billing': policy.billing_schedule,
            'named_insured': insured.name,
            'agent_name': agent.name,
            'schedules': available_schedules,
            'date': request.form['date']}

    return render_template('maintenance.html', passed_data=data)


@app.route('/payment/', methods=['POST'])
def payment():
    pa = PolicyAccounting(request.form['id'])
    pa.make_payment(request.form['payment_amount'], pa.policy.agent)
    return 'Payment successful!'


@app.route('/billing/', methods=['POST'])
def billing():
    pa = PolicyAccounting(request.form['id'])
    pa.change_billing_schedule(request.form['new_billing'])
    return 'Billing updated successfully!'


@app.route('/insured/', methods=['POST'])
def insured():
    pa = PolicyAccounting(request.form['id'])
    if not pa.update_named_insured(request.form['new_insured']):
        msg = 'Could not update the account. Is it canceled or expired?.'

    msg = 'Named-insured updated successfully!'
    return jsonify(text=msg,
                   name=request.form['new_insured'])
