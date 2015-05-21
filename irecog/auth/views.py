import stripe

from flask import current_app, render_template, \
    redirect, request, url_for, flash, session
from flask.ext.login import login_user, logout_user, login_required, \
    current_user

from . import auth
from .forms import LoginForm, RegistrationForm, ChangePasswordForm,\
    PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm
from .. import db
from ..models import User, Organization, Role, Award
from ..email import send_email, send_email_without_template
from ..main.helper_functions import get_or_create, slugify
from ..payment.models import Plan


@auth.before_app_request
def before_request():
    if current_user.is_authenticated():
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint[:5] != 'auth.' \
            and current_app.config['USER_EMAIL_CONFIRM_REQUIRED']:
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/register-admin', methods=['GET', 'POST'])
def register_org_admin():
    form = RegistrationForm()

    if form.validate_on_submit():
        email = form.email.data
        role = db.session.query(Role).filter_by(name='Organization Admin').first()

        # Set up Org
        org_name = form.organization_name.data
        org = Organization(name=org_name,
                           slug=slugify(org_name),
                           plan=Plan.query.filter_by(id=form.org_size.data).first()
        )
        db.session.add(org)

        # Set up User
        user = User(email=email,
                    password=form.password.data,
                    first_name=form.first_name.data,
                    last_name=form.last_name.data,
                    slug=slugify(email),
                    password_changed=True,
                    role=role,
                    organization=org,
        )

        # Set up a Stripe Customer
        cus = stripe.Customer.create(
            description=user.email,
            email=user.email,
            plan=org.plan.stripe_id
        )
        user.stripe_customer_id = cus.id
        db.session.add(user)

        # Generate email confirmation token link and send it
        session['registering'] = True
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm Your Account',
                   'auth/email/confirm', user=user, token=token)
        flash('Thank you for registering<br />'
              'A confirmation email has been sent to you by email.')
        login_user(user)

        # send email to admin
        send_email_without_template(current_app.config['ADMIN'], 'New user signed up',
                   user.email + ' Signed up',)
        return redirect(url_for('org.organization_admin_dashboard',
                                organization_slug=org.slug))

    plans = db.session.query(Plan).filter_by(live=True).order_by(Plan.amount)

    return render_template('auth/register_org_admin.html', form=form, plans=plans)


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous() or current_user.confirmed:
        return redirect('main.index')
    return render_template('auth/unconfirmed.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)

            # if a user is logging in for the first time, redirect to change password page
            if not user.password_changed:
                return redirect(url_for('auth.password_reset'))

            return redirect(request.args.get('next') or url_for('main.index'))
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """
    This is used when the user chooses 'Change Password" from their account page.
    """
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            current_user.password_changed = True
            db.session.add(current_user)
            flash('Your password has been updated.')
            if current_user.organization:
                return redirect(url_for('org.organization_admin_dashboard',
                                        organization_slug=current_user.organization.slug))
            else:
                return redirect(url_for('main.index'))
        else:
            flash('Invalid password.')
    return render_template("auth/change_password.html", form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    """
    This is used when user logs in for the first time after hr created them.
    They are required to put a new password.
    """
    if not current_user.is_anonymous():
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.password.data):
            flash('Your password has been updated.')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/change_lost_password.html', form=form)


@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous():
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset Your Password',
                       'auth/email/reset_password',
                       user=user, token=token,
                       next=request.args.get('next'))
        flash('An email with instructions to reset your password has been '
              'sent to you.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


def delete_user(user_id):
    user = User.query.filter_by(id=user_id).first()
    if user:
        db.session.delete(user)
        db.session.commit()
