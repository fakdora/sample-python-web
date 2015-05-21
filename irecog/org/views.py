import os

from flask import render_template, request, redirect, \
    url_for, flash, session, current_app
from flask.ext.login import login_required, current_user
from sqlalchemy import exc
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from . import org
from .forms import OrgAdminAddMemberForm, RecognitionForm, \
                 PrizeAddForm, AwardAddForm, CsvAddForm
from .helper_functions import delete_recognition, hide_recognition, show_recognition

from .. import db, stripe, stripe_keys
from ..auth.views import delete_user
from ..decorators import org_admin_required, org_member_required
from ..email import send_email
from ..main.helper_functions import get_or_create
from ..models import User, Organization, Recognition, Award
from ..payment.models import Plan, Card


@org.route('/organization/<organization_slug>',
           methods=['GET', 'POST'])
@login_required
@org_member_required
def recognition_page(organization_slug):
    error = None
    submitted = False
    org = Organization.query.filter_by(slug=organization_slug).first_or_404()
    form = RecognitionForm()

    if 'step4' in session:
        registering_now_step4 = True
        session.pop('step4', None)
    else: registering_now_step4 = False

    if form.validate_on_submit():
        nominee_data = form.nominee.data
        nominee = None
        for user in org.users.all():
            if nominee_data.lower() == user.name.lower():
                nominee = user
                break
        if nominee:
            recog = Recognition(award=org.current_award,
                                author=current_user,
                                reason=form.reason.data,
                                nominee=nominee,
                                organization=org,
                                approved=True
            )
            send_email(nominee.email, 'You\'ve Been Recognized!',
                       'org/email/your_recognized', user=nominee)
            db.session.add(recog)
            db.session.commit()
            submitted = True
        else:
            error = "That nominee is not found. Please check the name."
    return render_template('org/organization.html',
                            org=org, form=form, error=error, submitted=submitted,
                            registering_now_step4=registering_now_step4
    )


@org.route('/organization/<organization_slug>/billing',
           methods=['GET', 'POST']
)
@login_required
@org_admin_required
@org_member_required
def organization_admin_billing(organization_slug):

    if request.method == "POST":
        plan_id = request.form.get('plan')
        current_user.organization.plan = Plan.query.filter_by(id=plan_id).first()
        db.session.add(current_user.organization)
        try:
            db.session.commit()
        except IntegrityError:
            pass

        flash('Billing plan changed.')
        return redirect(url_for('org.organization_admin_dashboard',
                                organization_slug=organization_slug))

    return render_template('org/organization_billing.html')


@org.route('/organization/<organization_slug>/dashboard',
           methods=['GET', 'POST']
)
@login_required
@org_admin_required
@org_member_required
def organization_admin_dashboard(organization_slug):
    # These variables help with registering process steps
    employee_added = False
    registering_now_step3 = False
    registering_now_step2 = False
    if 'registering' in session:
        session.pop('registering', None)
        registering_now_step2 = True
        session['step3'] = True
    org = current_user.organization
    plan = Plan.query.filter_by(id=org.plan.id).first()

    if request.method == "POST":
        # If this post is stripe update payment
        cc_token = request.form.get('stripeToken', '')
        if cc_token:
            try:
                cus = stripe.Customer.retrieve(current_user.stripe_customer_id)
            except stripe.InvalidRequestError:
                cus = stripe.Customer.create(
                    description=current_user.email,
                    email=current_user.email,
                    plan=org.plan.stripe_id
                )
                current_user.stripe_customer_id = cus.id
                db.session.add(current_user)
                org.card_payer = current_user
                db.session.add(org)
            stripe_card = cus.cards.create(card=cc_token)
            cus.save()

            card = get_or_create(db.session,
                                  Card,
                                  stripe_customer_id=cus.id,
                                  user=current_user
                                  )
            card.last4=stripe_card.last4
            card.stripe_card_id=stripe_card.id
            card.stripe_customer_id=cus.id
            card.exp_month=stripe_card.exp_month
            card.exp_year=stripe_card.exp_year
            card.brand=stripe_card.brand
            card.country=stripe_card.country
            card.fingerprint=stripe_card.fingerprint
            card.user=current_user

            db.session.add(card)

            flash('Credit Card updated ')

        else: # If this post is for adding members
            index = 0
            existing_user = None
            # This is for adding members manually using ajax form
            while True:
                first_name_key = "first_name" + str(index)
                last_name_key = "last_name" + str(index)
                dept_key = "department" + str(index)
                email_key = "email" + str(index)

                first_name = request.form.get(first_name_key, '')
                if first_name:
                    index += 1
                    last_name = request.form.get(last_name_key, '')
                    dept = request.form.get(dept_key, '')
                    email = request.form.get(email_key, '')
                    existing_user = User.query.filter_by(email=email).first()

                    if existing_user:
                        flash('User with %s email address already exists' % email)
                        continue
                    user = User(first_name=first_name,
                                last_name=last_name,
                                department=dept,
                                email=email,
                                organization=org,
                                password="Have2Change")
                    db.session.add(user)
                    from sqlalchemy.exc import IntegrityError

                    try:
                        db.session.commit()
                    except IntegrityError:
                        pass
                else:
                    break
            if index == 1 and not existing_user:
                flash('New user is added.<br />'
                      'User can log in with his/her email address and <strong>Have2Change</strong> '
                      'as password.')
                employee_added = True
            elif index > 1:
                flash('New users are added.<br />'
                      'User can log in with his/her email address and <strong>Have2Change</strong> '
                      'as password.'
                )
                employee_added = True


    if employee_added and 'step3' in session:
        session.pop('step3', None)
        registering_now_step3 = True
        session['step4'] = True

    return render_template('org/organization_admin_dashboard.html',
                           plan=plan,
                           stripe_public=stripe_keys['publishable_key'],
                           registering_now_step2=registering_now_step2,
                           registering_now_step3=registering_now_step3,
                           employee_added=employee_added
    )


@org.route('/organization/members')
@login_required
@org_admin_required
def members_list():
    members = User.query.all()
    return render_template('org/admin_members_list.html', members=members)


@org.route('/organization/dashboard/award/add',
            methods = ['GET', 'POST'])
@login_required
@org_admin_required
def award_add():
    org = current_user.organization
    form = AwardAddForm()
    #form.department.choices = [(d.id, d.name) for d in Department.query.filter_by(organization=org)]

    if form.validate_on_submit():
        # if this is current, then make all exisitn ones into past ones
        if form.current.data:
            current_award = Award.query.filter_by(organization=org, current=True).first()
            if current_award:
                current_award.current = False
                db.session.add(current_award)

        award = get_or_create(db.session,
                                 Award,
                                 organization=org,
                                 name=form.name.data,
                                 current=form.current.data,
                                 hide=False)
        db.session.add(award)
        flash('Award is added.')
        return redirect(url_for('org.organization_admin_dashboard',
                                organization_slug=org.slug))
    return render_template('org/organization_add_award.html', form=form)


@org.route('/organization/dashboard/award/<int:award_id>/delete/',
            methods = ['DELETE'])
@login_required
@org_admin_required
def award_delete(award_id):
    cat = Award.query.filter_by(id=award_id).first()
    if cat:
        db.session.delete(award_id)
        db.session.commit()
    flash('An Award is removed.')
    return redirect(url_for('org.organization_admin_dashboard',
                            organization_slug=current_user.organization.slug))


@org.route('/organization/dashboard/card/add',
            methods = ['GET', 'POST'])
@login_required
@org_admin_required
def credit_card_add():
    org = current_user.organization
    form = PrizeAddForm()

    if form.validate_on_submit():
        org.prize = form.prize.data
        db.session.add(org)
        db.session.commit()
        flash('A Prize is updated.')
        return redirect(url_for('org.organization_admin_dashboard',
                                organization_slug=org.slug))
    return render_template('org/organization_add_prize.html', form=form)


@org.route('/organization/dashboard/card/delete',
            methods = ['DELETE'])
@login_required
@org_admin_required
def credit_card_delete():
    org = current_user.organization
    org.prize = None
    db.session.add(org)
    db.session.commit(org)

    flash('A Prize is updated.')
    return redirect(url_for('org.organization_admin_dashboard',
                            organization_slug=org.slug))


@org.route('/organization/dashboard/prize/add',
            methods = ['GET', 'POST'])
@login_required
@org_admin_required
def prize_add():
    org = current_user.organization
    form = PrizeAddForm()

    if form.validate_on_submit():
        org.prize = form.prize.data
        db.session.add(org)
        db.session.commit()
        flash('A Prize is updated.')
        return redirect(url_for('org.organization_admin_dashboard',
                                organization_slug=org.slug))
    return render_template('org/organization_add_prize.html', form=form)


@org.route('/organization/dashboard/prize/delete',
            methods = ['DELETE'])
@login_required
@org_admin_required
def prize_delete():
    org = current_user.organization
    org.prize = None
    db.session.add(org)
    db.session.commit(org)

    flash('A Prize is updated.')
    return redirect(url_for('org.organization_admin_dashboard',
                            organization_slug=org.slug))


@org.route('/organization/dashboard/user/add',
            methods = ['GET', 'POST'])
@login_required
@org_admin_required
def member_add_manually():
    org = current_user.organization
    form = OrgAdminAddMemberForm()

    if form.validate_on_submit():

        user = User(email=form.email.data,
                    position=form.position.data,
                    organization=org,
                    first_name=form.first_name.data,
                    last_name=form.last_name.data,
                    password='pass',
        )
        db.session.add(user)
        db.session.commit()
        flash('A member is added.')
        return redirect(url_for('org.organization_admin_dashboard',
                                organization_slug=org.slug))

    return render_template('org/organization_add_member.html', form=form)


@org.route('/organization/dashboard/user/delete/<int:user_id>',
            methods = ['GET', 'POST'])
@login_required
@org_admin_required
def member_delete(user_id):
    if current_user.id != user_id:
        delete_user(user_id)
        flash('A member is removed.')
    return redirect(url_for('org.organization_admin_dashboard',
                            organization_slug=current_user.organization.slug))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in {'CSV', 'csv'}


@org.route('/organization/import/users', methods=['GET', 'POST'])
def upload_csv_file():
    form = CsvAddForm()

    if form.validate_on_submit():
        file = form.csv_file.file

        if file and allowed_file(file.filename):

            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            import csv
            from collections import namedtuple

            # CSV has to be in this format
            # Columns as shown in that order, without the header. (email address type is not important here)
            EmployeeRecord = namedtuple('EmployeeRecord', 'name, email, department_name, position')
            employees = []
            # make list of namedtuple employee objects
            for line in csv.reader(open(os.path.join(current_app.config['UPLOAD_FOLDER'], filename), "rU")):
                emp = EmployeeRecord._make(line)
                employees.append(emp)
                print emp.name, emp.email, emp.department_name, emp.position

            for e in employees:
                try:
                    user = User(email=e.email,
                                first_name=e.first_name,
                                last_name=e.last_name,
                                organization=current_user.organization,
                                position=e.position,
                                password='pass')
                    db.session.add(user)
                    db.session.commit()
                except exc.IntegrityError:
                    db.session.rollback()


            return redirect(url_for('org.organization_admin_dashboard',
                                organization_slug=current_user.organization.slug))

    return render_template('org/organization_import_csv.html', form=form,
                           emailto=current_app.config['SUPPORT_EMAIL']
                           )


@org.route('/recogs/delete/<int:id>',
            methods = ['GET', 'POST'])
@login_required
@org_admin_required
def recognition_delete(id):
    delete_recognition(id)
    flash('Recognition is deleted.')
    return redirect(url_for('org.organization_admin_dashboard',
                            organization_slug=current_user.organization.slug))


@org.route('/recogs/hide/<int:id>',
            methods = ['GET', 'POST'])
@login_required
@org_admin_required
def recognition_hide(id):
    hide_recognition(id)
    flash('Recognition will not show up.')
    return redirect(url_for('org.organization_admin_dashboard',
                            organization_slug=current_user.organization.slug))


@org.route('/recogs/approve/<int:id>',
            methods = ['GET', 'POST'])
@login_required
@org_admin_required
def recognition_show(id):
    show_recognition(id)
    flash('Recognition is approved')
    return redirect(url_for('org.organization_admin_dashboard',
                            organization_slug=current_user.organization.slug))


@org.route('/recogs/winner/<int:id>',
            methods = ['GET', 'POST'])
@login_required
@org_admin_required
def recognition_winnner(id):
    r = Recognition.query.filter_by(id=id).first()
    r.winner = True
    if r:
        db.session.add(r)
        db.session.commit()
    flash('Winner chosen')
    return redirect(url_for('org.organization_admin_dashboard',
                            organization_slug=current_user.organization.slug))


@org.route('/recogs/unselect_winner/<int:user_id>',
            methods = ['GET', 'POST'])
@login_required
@org_admin_required
def recognition_change_winner_status(user_id):
    r = Recognition.query.filter_by(id=user_id).first()
    r.winner = False
    if r:
        db.session.add(r)
    flash('Winner unselected')
    return redirect(url_for('org.organization_admin_dashboard',
                            organization_slug=current_user.organization.slug))
