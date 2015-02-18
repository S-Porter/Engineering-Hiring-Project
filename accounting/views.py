# You will probably need more methods from flask but this one is a good start.
from flask import render_template, redirect, request, flash, url_for
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
        date_cursor = datetime.strptime(request.form['date'], '%Y-%m-%d')
        date_cursor = date_cursor.date()

    policies = Policy.query.filter_by(id=request.form['id']).all()
    if not policies:
        flash("Entered policy id wasn't found, please try a different policy ID.")
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
            'date_cursor': date_cursor,
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