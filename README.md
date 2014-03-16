Pjuu
====

Open source social networking site which runs 'pjuu.com'.

This is an open source project released under the GNU AGPL v3. See LICENSE for more details.

Development Information
-----------------------

Pjuu is written in Python and uses the excellent Flask web framework.

We use Redis as our sole data store. This is a key-value store which is capable of storing various data types.

If you want to take a look at how data is inserted and queried take a look in each of the modules at 'backend.py'. All functions which speak to Redis are stored in these files. This removes any Redis code from the web facing functions stored in the modules as 'views.py.
