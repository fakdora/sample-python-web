from datetime import datetime
from app.models import db


class Plan(db.Model):
    __tablename__ = 'payment_plans'
    id = db.Column(db.Integer, primary_key=True)

    stripe_id = db.Column(db.String(20))
    amount = db.Column(db.Integer())
    name = db.Column(db.String(40))
    display_name = db.Column(db.String(40))
    display_amount = db.Column(db.String(10))
    display_users = db.Column(db.String(15))
    description = db.Column(db.String(20))
    trial_period_days = db.Column(db.SmallInteger())
    live = db.Column(db.Boolean, default=False)
    organizations = db.relationship('Organization', backref='plan', lazy='dynamic')
    
    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return 'Plan: %s $%d - id:%d' % (self.name, self.amount/100, self.id)


class Card(db.Model):
    __tablename__ = 'stripe_cards'

    id = db.Column(db.Integer, primary_key=True)
    stripe_card_id = db.Column(db.String(64))
    stripe_customer_id = db.Column(db.String(64))
    brand = db.Column(db.String(32))
    last4 = db.Column(db.String(4))
    exp_month = db.Column(db.String(2))
    exp_year = db.Column(db.String(4))
    country = db.Column(db.String(2))
    funding = db.Column(db.String(12))
    fingerprint = db.Column(db.String(64))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return 'Card: %d for %s, %s' % (self.id, self.last4, self.user)
