from threading import Thread
from flask import current_app, render_template
from flask.ext.mail import Message
from . import mail


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, sender=None, **kwargs):
    app = current_app._get_current_object()

    if not isinstance(to, (list, tuple)):
        to = [to]
    if sender:
        sender_email = sender
    else:
        sender_email = app.config['MAIL_SENDER']
    msg = Message(app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=sender_email, recipients=to)

    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr


def send_email_without_template(to, subject, msg_body, sender=None, **kwargs):
    app = current_app._get_current_object()

    if not isinstance(to, (list, tuple)):
        to = [to]

    if sender:
        sender_email = sender
    else:
        sender_email = app.config['MAIL_SENDER']

    subject = app.config['MAIL_SUBJECT_PREFIX'] + ' ' + subject
    msg = Message(subject,sender=sender_email, recipients=to)

    msg.body = msg_body

    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
