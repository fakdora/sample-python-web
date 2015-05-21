from .. import db
from ..models import Recognition

def delete_recognition(rid):
    r = Recognition.query.filter_by(id=rid).first()
    if r:
        db.session.delete(r)
        db.session.commit()


def hide_recognition(rid):
    r = Recognition.query.filter_by(id=rid).first()
    r.approved = False
    if r:
        db.session.add(r)
        db.session.commit()


def show_recognition(rid):
    r = Recognition.query.filter_by(id=rid).first()
    r.approved = True
    if r:
        db.session.add(r)
        db.session.commit()