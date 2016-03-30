# -*- coding: utf8 -*-

"""For all current users create their 2 system romps (public, pjuu)

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2016 Joe Doherty

"""

import inspect
import os
import sys

currentdir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from pjuu import create_app, mongo as m
from pjuu.users.backend import create_romp

if __name__ == '__main__':
	app = create_app()
	ctx = app.app_context()
	ctx.push()

	for user in m.db.users.find():
		create_romp(user.get('_id'), 'public', special=True)
		create_romp(user.get('_id'), 'pjuu', special=True)
		print "created for", user.get('username')

	ctx.pop()