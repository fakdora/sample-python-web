from functools import wraps
from flask import abort
from flask.ext.login import current_user
from .models import Permission, Organization


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def is_org_member():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            org = Organization.query.filter_by(slug=kwargs['organization_slug']).first_or_404()
            if current_user.organization != org:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def super_admin_required(f):
    return permission_required(Permission.SUPER_ADMIN)(f)


def org_admin_required(f):
    return permission_required(Permission.MODERATE_ORGANIZATION)(f)


def org_member_required(f):
    return is_org_member()(f)
