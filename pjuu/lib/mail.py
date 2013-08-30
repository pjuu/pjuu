from flask.ext.mail import Message

from pjuu import mail


def send_mail(subject, recipients, text_body='', html_body=''):
    '''
    Sends e-mail via flask-mail
    '''
    msg = Message(subject, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)
