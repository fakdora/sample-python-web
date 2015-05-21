import hashlib
from datetime import datetime
from dateutil.relativedelta import relativedelta
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request
from flask.ext.login import UserMixin, AnonymousUserMixin
from app import db, login_manager


class Permission:
    """
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80
    """

    WRITE_RECOGNITION = 0x01
    MODERATE_RECOGNITION = 0x02
    MODERATE_WINNER = 0x04
    MODERATE_USERS = 0x08
    MODERATE_ORGANIZATION = 0x10
    SUPER_ADMIN = 0x80

    roles = {
        'User': (WRITE_RECOGNITION, True), # 0x01
        'Organization Admin': (WRITE_RECOGNITION | # 0x1f
                               MODERATE_RECOGNITION |
                               MODERATE_WINNER |
                               MODERATE_USERS |
                               MODERATE_ORGANIZATION, False),
        'Moderator': (WRITE_RECOGNITION |
                      MODERATE_RECOGNITION |
                      MODERATE_USERS |
                      MODERATE_WINNER |
                      MODERATE_ORGANIZATION, False),
        'Super Administrator': (0xff, False)
    }

    @staticmethod
    def org_admin():
        return (Permission.WRITE_RECOGNITION |
                Permission.MODERATE_RECOGNITION |
                Permission.MODERATE_WINNER |
                Permission.MODERATE_USERS |
                Permission.MODERATE_ORGANIZATION)


class Organization(db.Model):
    __tablename__ = 'organizations'
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))
    slug = db.Column(db.String(100), unique=True)

    default = db.Column(db.Boolean, default=False, index=True) # what the fuck is this?
    users = db.relationship('User', backref='organization', lazy='dynamic')
    #departments = db.relationship('Department', backref='organization', lazy='dynamic')
    #recog_categories = db.relationship('RecognitionCategory', backref='organization', lazy='dynamic')
    recognitions = db.relationship('Recognition', backref='organization', lazy='dynamic')
    awards = db.relationship('Award', backref='organization', lazy='dynamic')
    prize = db.Column(db.String(64))
    #subscription_plan_id = db.Column(db.String(64))
    subscription_plan_id = db.Column(db.Integer, db.ForeignKey('payment_plans.id'))

    # hook up payer user and its credit card
    card_payer = db.relationship("User", uselist=False)

    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return 'Org %r' % (self.name)

    @property
    def free_until(self):
        free_trial_days = current_app.config['FREE_TRIAL_DAYS']
        return self.created.date() + relativedelta(days=+free_trial_days)

    @property
    def is_free_plan(self):
        if self.plan.stripe_id == 'free':
            return True
        else: return False

    @property
    def credit_card_updated(self):
        if self.card_payer:
            return True
        else: return False

    @property
    def current_award(self):
        return Award.query.filter_by(organization=self,
                                     current=True,
                                     hide=False).first()
    @property
    def past_awards(self):
        return Award.query.filter_by(organization=self,
                                     current=False).all()

    @property
    def org_size(self):
        return len(self.users)




#def after_insert_listener_org(mapper, connection, target):
    # 'target' is the inserted object
#    pass
#event.listen(Organization, 'after_insert', after_insert_listener_org)



class Recognition(db.Model):
    __tablename__ = 'recognitions'
    id = db.Column(db.Integer, primary_key=True)

    reason = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    nominee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    winner = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)
    approved = db.Column(db.Boolean, default=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    award_id = db.Column(db.Integer, db.ForeignKey('awards.id'))

    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return 'Recognition: %r' % self.nominee


class Award(db.Model):
    __tablename__ = 'awards'
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(64))
    current = db.Column(db.Boolean, default=False)
    hide = db.Column(db.Boolean, default=False)
    recognitions = db.relationship('Recognition', backref='award', lazy='dynamic')
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))

    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return '<Award %r, Org %r>' % (self.name, self.organization)

    @property
    def display_name(self):
        try:
            return self.name.split()[0]
        except IndexError:
            return None


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')
    created = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    modified = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    @staticmethod
    def insert_roles():
        for r in Permission.roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = Permission.roles[r][0]
            role.default = Permission.roles[r][1]
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return 'Role %r' % self.name


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True)

    email = db.Column(db.String(64), unique=True, index=True)

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    department = db.Column(db.String(100))
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False) #dlee change it later to false
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))

    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    invitation_email_sent = db.Column(db.Boolean, default=False)
    password_changed = db.Column(db.Boolean, default=False)

    #subscription = db.relationship("Subscription", uselist=False, backref="user")
    #active_until = db.Column(db.DateTime())

    stripe_customer_id = db.Column(db.String(64))
    team_name = db.Column(db.String(64))
    team_id = db.Column(db.Integer, unique=True)

    position = db.Column(db.String(64))


    recognitions = db.relationship('Recognition',
                                 foreign_keys=[Recognition.nominee_id],
                                 backref=db.backref('nominee', lazy='joined'),
                                 lazy='dynamic', cascade='all, delete-orphan')

    authored = db.relationship('Recognition',
                               foreign_keys=[Recognition.creator_id],
                               backref=db.backref('author', lazy='joined'),
                               lazy='dynamic', cascade='all, delete-orphan')

    cards = db.relationship('Card', backref='user',
                                lazy='dynamic')


    def __repr__(self):
        return 'User %r %s' % (self.email, self.organization )

    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email=forgery_py.internet.email_address(),
                     password=forgery_py.lorem_ipsum.word(),
                     confirmed=False,
                     first_name=forgery_py.name.first_name(),
                     last_name=forgery_py.name.last_name(),
                     location=forgery_py.address.city(),
                     about_me=forgery_py.lorem_ipsum.sentence(),
                     member_since=forgery_py.date.date(True))
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.email.encode('utf-8')).hexdigest()

    def write_recognition(self, user, description):
        r = Recognition(author=self, nominee=user, description=description)
        db.session.add(r)

    @property
    def name(self):
        return "%s %s" % (self.first_name, self.last_name)

    @property
    def past_received_recognitions(self):
        return self.recognitions.all()

    @property
    def past_authored_recognitions(self):
        return self.authored.all()

    @property
    def past_wins(self):
        return self.recognitions.filter_by(winner=True)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True

    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions

    def is_super_admin(self):
        return self.can(Permission.SUPER_ADMIN)

    def is_org_admin(self):
        return self.organization and self.can(Permission.MODERATE_ORGANIZATION)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_super_admin(self):
        return False

    def is_org_admin(self):
        return False
login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


