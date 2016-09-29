# -*- coding: utf8 -*-

"""Converts older Pjuu storage (MongoDB) to PostgreSQL.

:license: AGPL v3, see LICENSE for more details
:copyright: 2014-2016 Joe Doherty

"""

import pymongo  # noqa


m = pymongo.MongoClient(host='localhost')
r = StrictRedis()


if __name__ == '__main__':
