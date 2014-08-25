# -*- coding: utf8 -*-

"""
Description:
    Tests for library modules.

    Note: Each module should be split in to it's own test case!
    Note: Most of these tests should extend BackendTestCase, nothing in the lib
          module should ever need testing from a front end point of view

Licence:
    Copyright 2014 Joe Doherty <joe@pjuu.com>

    Pjuu is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Pjuu is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


from .test_helpers import BackendTestCase


class AlertTests(BackendTestCase):

    def test_create_alert(self):
        self.assertTrue(1 + 1, 2)
