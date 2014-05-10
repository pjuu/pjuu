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

# 3rd party imports
from flask.ext.wtf import Form
from wtforms import TextAreaField, TextField
from wtforms.validators import Length, Required


class ChangeProfileForm(Form):
    """ This is the form used to update your about information """
    about = TextAreaField('About', [Required(), Length(max=255,
               message='Your about can not be larger than 255 characters')])


class SearchForm(Form):
	""" This form is really simple. It is here to keep all forms at WTFroms """
	query =  TextField("Query")