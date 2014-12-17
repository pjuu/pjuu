# Pjuu

```
Pjuu is under very active development at this early stage in its life. A lot
may change between versions until we are happy with it :)
```

[![Build Status](https://travis-ci.org/pjuu/pjuu.svg?branch=master)](https://travis-ci.org/pjuu/pjuu=master) [![Coverage Status](https://coveralls.io/repos/pjuu/pjuu/badge.png?branch=master)](https://coveralls.io/r/pjuu/pjuu?branch=master) [![Requirements Status](https://requires.io/github/pjuu/pjuu/requirements.svg?branch=master)](https://requires.io/github/pjuu/pjuu/requirements/?branch=master) [![Documentation Status](https://readthedocs.org/projects/pjuu/badge/?version=master&style=default)](https://pjuu.readthedocs.org/en/master/) [![License](https://img.shields.io/badge/license-AGPLv3-brightgreen.svg)](http://www.gnu.org/licenses/agpl-3.0.en.html) [![Hipchat](http://img.shields.io/badge/chat-hipchat-blue.svg)](http://www.hipchat.com/gpbvQy6JF)

An open-source social networking application which runs https://pjuu.com.

This is an open source project released under the GNU AGPLv3 license. See LICENSE for more details or visit the official GNU page at http://www.gnu.org/licenses/agpl-3.0.html.

### About

This is the primary code base for https://pjuu.com, the website is deployed directly from this respository.

The main goal of Pjuu as an application is privacy.

Pjuu is written in Python/Flask and uses Redis and MongoDB as the data stores.

### Getting started

Getting started working on Pjuu or deploying it yourself is quite easy. We will only cover development here and the following documentation is for Debian 7 (Wheezy) Linux (we are big fans), this should work with Ubuntu also.

We are presuming a fresh installation, this will setup the environment:

Note: This will install Redis from wheezy-backports you may want to change this. Wheezy backports uses Redis version 2.8, you may already have a newer version, in Ubuntu for example.

Note: This will install MongoDB from 10gen's own Debian repository. This is not always needed and your own distributions repository may do.

```
$ sudo apt-key adv --keyserver keyserver.ubuntu.com --recv 7F0CEB10

$ sudo sh -c 'echo "deb http://ftp.uk.debian.org/debian wheezy-backports main" >> /etc/apt/sources.list'

$ sudo sh -c 'echo "deb http://downloads-distro.mongodb.org/repo/debian-sysvinit dist 10gen" >> /etc/apt/sources.list'

$ sudo apt-get update

$ sudo apt-get install build-essentials python-dev python-setuptools

$ sudo apt-get install -t wheezy-backports redis-server

$ ssudo apt-get install mongodb-org

$ sudo easy_install virtualenv

$ git clone https://github.com/pjuu/pjuu.git

$ cd pjuu

$ virtualenv venv

$ source venv/bin/activate

$ pip install -r requirements.txt
```

Running the unit tests:

```
$ python run_tests.py
```

Running the unit tests with coverage:

```
$ coverage run --source=pjuu --omit=pjuu/wsgi.py,*.html,*.txt run_tests.py
```

Running the development server (CherryPy):

```
$ python run_server.py
```

You can view the site by visiting: http://localhost:5000

You can now play with the code base :)

```
This may not be 100% complete. If you find any issues with these instructions
please open an Issue or send us a pull request :)
```

### Contributing

We are open to all pull requests. Spend some time taking a look around, locate a bug, design issue or spelling mistake then send us a pull request :)

### Security

All software has bugs in and Pjuu is no different. These may have security implications. If you find one that you suspect could allow you to do something you shouldn't be able to please do not post it as an issue on Github. We would really appreciate it if you could send an e-mail to security@pjuu.com with the relevant details.

### Credits

James Rand - illustrating our Otter logo :)
