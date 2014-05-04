# Pjuu

An open-source social networking application which runs https://pjuu.com.

This is an open source project released under the GNU AGPL v3. See LICENSE for more details.

## About

The goal of Pjuu is to provide an online community but one where you are in control of your data.

Our main priority is our users privacy. When you no longer want to use the site you can delete your account. This will remove all data that is held on you. This includes your account, every post you made, every comment you made, and everything in between.

Once your account is gone from the site it will only be help in backups for 7 days, the same goes for all web logs so within a week of deleting you can be confident your data is gone.

We are also trying to remove our reliance on external services, soon to go are ReCaptcha and Gravatar. This way you can be sure your online activity on Pjuu is known only by Pjuu and NO ONE else.

If you want to help out why not contribute on Github?

Our aim is to be as open and transparent as possible about the site; pjuu.com pulls for this Github repository to the live site there is no hidden code in between.

## Development Information

Pjuu is written in Python and uses the excellent Flask web framework.

We use Redis as our sole data store. This is a key-value store which is capable of storing various data types.

If you want to take a look at how data is inserted and queried take a look in each of the modules at 'backend.py'. All functions which speak to Redis are stored in these files. This removes any Redis code from the web facing functions stored in the modules as 'views.py'.

Design Information
------------------

Please be aware that at pjuu.com we use the royalty-free copy of Glyphicons from glyphicons.com

This means we can not add them in to our repository. We may include the free versions at some point in the future. You will need to add Glyphicons in to the "/static/img/glyphicons" and rename them to the same name we use here. I am aware this will be a pain but unfortunatley we are going to have to come up with a work around.