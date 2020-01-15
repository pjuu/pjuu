# -*- coding: utf8 -*-

"""Simple wrapper for sending e-mail

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2020 Joe Doherty

"""

# 3rd party imports
from flask import current_app as app
from flask_mail import Message
# Pjuu imports
from pjuu import celery, mail


def send_mail(subject, recipients, sender=None,
              text_body='', html_body=''):
    """Wrapper to send mail async over celery"""
    send_async_mail.delay(subject, recipients, sender=sender,
                          text_body=text_body, html_body=html_body)


@celery.task()
def send_async_mail(subject, recipients, sender=None,
                    text_body='', html_body=''):
    """Actually send a use an email"""
    # Set the default sender if one is not supplied
    if sender is None:  # pragma: no branch
        sender = app.config['MAIL_DEFAULT_SENDER']

    msg = Message()
    msg.subject = subject
    msg.recipients = recipients
    msg.sender = sender
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)
