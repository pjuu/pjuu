#!/usr/bin/env python
import getpass
import sys
import os.path

from cherrypy import wsgiserver

from pjuu import app, db
from pjuu.users.models import User


if __name__ == '__main__':

    if len(sys.argv) >= 2:
        if sys.argv[1] == 'run':
            """
            Run the Flask development server
            """
            d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
            server = wsgiserver.CherryPyWSGIServer(('0.0.0.0', 5000), d)
            try:
                server.start()
            except KeyboardInterrupt:
                server.stop()
        elif sys.argv[1] == 'createdb':
            """
            Will create all tables in the database.
            """
            print "Creating database..."
            db.create_all()
            print "Complete"
        elif sys.argv[1] == 'dropdb':
            """
            Will drop all tables in the database.
            """
            print "Dropping database..."
            db.drop_all()
            print "Complete"
        elif sys.argv[1] == 'createuser':
            """
            Will add an active user to Pjuu.
            """
            username = raw_input('User Name: ')
            email = raw_input('E-Mail: ')
            password = getpass.getpass()
            isstaff = raw_input('Staff? (y/n): ')
            new_user = User(username, email, password)
            if isstaff.lower() == 'y':
                new_user.is_staff = True
            new_user.is_active = True
            db.session.add(new_user)
            db.session.commit()
        else:
            print "Unknown command: %s" % sys.argv[1]
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s run|createdb|dropdb|createjoe" % sys.argv[0]
        sys.exit(2)
