from flask import current_app, render_template, request, flash
from flask.ext.login import login_required, current_user

from . import main
from .forms import ContactForm
from .. import stripe_keys
from ..email import send_email_without_template


@main.route('/', methods=['GET', 'POST'])
def index():
    form = ContactForm()
    return render_template('index.html', form=form)


@main.route('/stripe')
@login_required
def stripe():
    return render_template('stripe/stripe.html', key=stripe_keys['publishable_key'],
                           current_user=current_user)

@main.route('/stripe-custom', methods=['POST'])
def stripecustom():
    return render_template('stripe_custom.html', key=stripe_keys['publishable_key'])


@main.route('/stripe/charge', methods=['POST'])
def charge():
    # Amount in cents
    import stripe
    plan = request.form['plan']
    description = "%s - %s Monthly" % (current_user.email, plan)
    try:
        customer =  stripe.Customer.create(
            email=current_user.email,
            card=request.form['stripeToken'],
            plan=plan,
            description=description
        )
    except stripe.error.CardError, e:
        # Since it's a decline, stripe.error.CardError will be caught
        body = e.json_body
        err = body['error']

        print "Status is: %s" % e.http_status
        print "Type is: %s" % err['type']
        print "Code is: %s" % err['code']
        # param is '' in this case
        print "Param is: %s" % err['param']
        print "Message is: %s" % err['message']
    except stripe.error.InvalidRequestError, e:
        # Invalid parameters were supplied to Stripe's API
        pass
    except stripe.error.AuthenticationError, e:
        # Authentication with Stripe's API failed
        # (maybe you changed API keys recently)
        pass
    except stripe.error.APIConnectionError, e:
        # Network communication with Stripe failed
        pass
    except stripe.error.StripeError, e:
        # Display a very generic error to the user, and maybe send
        # yourself an email
        pass
    except Exception, e:
        # Something else happened, completely unrelated to Stripe
        pass

    return render_template('stripe_charge.html', plan=plan)


@main.route('/legal')
def legal():
    return render_template('legal.html')


@main.route('/faq')
def faq():
    return render_template('faq.html')

@main.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    template_name = 'contact/contact.html'

    if request.method == 'POST':
        app = current_app._get_current_object()
        if form.validate() == False:
            flash('All fields are required.')
            return render_template(template_name, form=form)
        else:
            message = "From: " + form.email.data + "\n"
            message += form.message.data
            send_email_without_template(app.config['ADMINS'],
                                        "[iRecog Contact] " + form.subject.data,
                                        message,
                                        )

            return render_template(template_name, form=form, sent=True)
    elif request.method == 'GET':
        return render_template(template_name, form=form)


@main.route('/testemail')
def testemail():
    from flask.ext.mail import Message
    from .. import mail
    from flask import current_app
    app = current_app._get_current_object()
    msg = Message('test subject', sender=current_app.config['ADMINS'][0], recipients=['davidleesd@hotmail.com'])
    msg.body = 'text body'
    msg.html = '<b>HTML</b> body'
    with app.app_context():
        mail.send(msg)
    return 'sent'