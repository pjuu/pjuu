# -*- coding: utf8 -*-
from flask.ext.mail import Message
from pjuu import app, mail


def send_mail(subject, recipients, sender=app.config['MAIL_DEFAULT_SENDER'],
              text_body='', html_body=''):
    '''
    Sends e-mail via flask-mail
    '''
    msg = Message()
    msg.subject = subject
    msg.recipients = recipients
    msg.sender = sender
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)
