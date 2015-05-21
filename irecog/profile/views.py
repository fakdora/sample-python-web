from flask import render_template, redirect, url_for, abort, flash
from flask import request
from flask.ext.login import login_required, current_user

from . import profile
from .forms import EditProfileForm, EditProfileOrgAdminForm
from .. import db
from ..models import Role, User
from ..decorators import org_admin_required

@profile.route('/user/<int:id>', methods=['GET', 'POST'])
def user(id):
    user = User.query.filter_by(id=id).first_or_404()

    if request.method == "POST":
        index = 0
        while True:
            first_name_key = "first_name"+ str(index)
            last_name_key = "last_name" + str(index)
            dept_key = "department" + str(index)
            email_key = "email" + str(index)

            first_name = request.form.get(first_name_key, '')
            if first_name:
                last_name = request.form.get(last_name_key, '')
                dept = request.form.get(dept_key, '')
                email = request.form.get(email_key, '')
                user = User(first_name=first_name, last_name=last_name,
                            department=dept, email=email,
                            organization=current_user.organization,
                            password="pass")
                db.session.add(user)
                from sqlalchemy.exc import IntegrityError
                try:
                    db.session.commit()
                except IntegrityError:
                    pass
                index += 1
            else:
                break
            flash('New user added.')

    if current_user.organization != user.organization and \
        not current_user.is_super_admin():
        abort(403)

    return render_template('profile/profile.html', user=user)


@profile.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        current_user.department = form.department.data
        current_user.position = form.position.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user', id=current_user.id))
    form.first_name.data = current_user.first_name
    form.last_name.data = current_user.last_name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    form.department.data = current_user.department
    form.position.data = current_user.position
    return render_template('profile/edit_profile.html', form=form)


def redirect_url():
    return request.args.get('next') or \
           request.referrer or \
           url_for('index')


@profile.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@org_admin_required
def edit_profile_org_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileOrgAdminForm(user=user)

    if form.validate_on_submit():
        user.email = form.email.data
        user.role = Role.query.get(form.role.data)
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        user.department = form.department.data
        user.position = form.position.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(redirect_url())

    form.email.data = user.email
    form.role.data = user.role_id
    form.first_name.data = user.first_name
    form.last_name.data = user.last_name
    form.location.data = user.location
    form.about_me.data = user.about_me
    form.position.data = user.position
    form.department.data = user.department

    return render_template('profile/edit_profile_as_org_admin.html',
                           form=form, user=user)
