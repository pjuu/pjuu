# -*- coding: utf8 -*-

##############################################################################
# Copyright 2014 Joe Doherty <joe@pjuu.com>
#
# Pjuu is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pjuu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
##############################################################################

from flask.ext.mail import Message
from pjuu import app, mail


def send_mail(subject, recipients, sender=app.config['MAIL_DEFAULT_SENDER'],
              text_body='', html_body=''):
    """
    Sends e-mail via flask-mail
    """
    msg = Message()
    msg.subject = subject
    msg.recipients = recipients
    msg.sender = sender
    msg.body = text_body
    msg.html = html_body
    # If no mail is set then an e-mail will not actually be sent it will have
    # its subject, sender, recipient sent to stdout
    if not app.config['NO_MAIL']:
        mail.send(msg)
    elif app.debug:
        # Allow users to turn off NO_MAIL and display a print only in debug
        print "Mail:", msg.subject, msg.recipients, msg.sender
