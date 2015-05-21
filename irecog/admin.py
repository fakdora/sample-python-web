from flask import redirect, url_for, request, render_template
from flask.ext.admin import Admin, BaseView, expose, AdminIndexView
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.login import current_user


class MyAdminHomeView(AdminIndexView):
    @expose('/')
    def index(self):
        return self.render('admin/index.html')

    def is_accessible(self):
        return current_user.is_super_admin()


class MyAdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_super_admin()


class RoleAdminView(MyAdminModelView):
    # Disable model creation
    can_create = False

    # Override displayed fields
    column_list = ('name', 'default')

    def __init__(self, session, **kwargs):
        from .models import Role
        # You can pass name and other parameters if you want to
        super(RoleAdminView, self).__init__(Role, session, **kwargs)


class MyAdminView(BaseView):
    @expose('/')
    def index(self):
        if current_user.is_super_admin():
            return self.render('admin/index.html')

        return self.render('admin/fail.html')

    def is_accessible(self):
        return current_user.is_super_admin()

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('login', next=request.url))


def register_admin(admin):
    from app.models import User, Recognition, Organization
    from payment.models import Card, Plan
    from . import db

    admin.add_view(MyAdminModelView(User, db.session, name="User", category='Auth'))
    admin.add_view(RoleAdminView(db.session, name="Role", category='Auth'))

    admin.add_view(MyAdminModelView(Recognition, db.session, name="Recognition", category='Org'))
    admin.add_view(MyAdminModelView(Organization, db.session, name="Organization", category='Org'))

    admin.add_view(MyAdminModelView(Plan, db.session, name="Plan", category='Payment'))
    admin.add_view(MyAdminModelView(Card, db.session, name="Card", category='Payment'))


