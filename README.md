Pjuu
====

Social networking thingy

Dependencies
------------

Pjuu by default uses SQLite so there is no DBMS dependencies. You can switch this later through SQLAlchemy connection string. ILIKE is used so that SQLite is compatible with MySQL.

The only dependencies system wise is **Redis**. This is used for session by default. If you know what you are doing you can remove this however. I always use this on my development server.

Work on it
----------

Setup the development environment:
```
$ git clone git@github.com:pjuu/pjuu.git
$ cd pjuu
$ virtualenv env
$ pip install -r requirements.txt
$ . env/bin/activate
$ cp pjuu/settings_example.py pjuu/settings.py
```
Hack away. Pjuu uses SQLite by default.
