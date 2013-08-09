#!/usr/bin/env python

from pjuu import db

print "Creating database and tables..."
db.create_all()
print "Complete"
