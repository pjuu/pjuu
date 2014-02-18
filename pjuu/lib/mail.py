# -*- coding: utf8 -*-
from flask.ext.mail import Message
from pjuu import mail


def send_mail(subject, recipients, sender='Pjuu <noreply@pjuu.com>',
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
