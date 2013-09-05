#!/usr/bin/env python
import sys

from pjuu import app, db

if __name__ == '__main__':

    if len(sys.argv) >= 2:
        if sys.argv[1] == 'run':
            app.run(host='0.0.0.0')
        elif sys.argv[1] == 'createdb':
            print "Creating database..."
            db.create_all()
            print "Complete"
        elif sys.argv[1] == 'migratedb':
            pass
        else:
            print "Unknown command: %s" % sys.argv[1]
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s run|createdb|migratedb" % sys.argv[0]
        sys.exit(2)
