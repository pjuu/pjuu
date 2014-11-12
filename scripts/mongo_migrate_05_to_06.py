# -*- coding: utf8 -*-

"""
Description:
    We have moved on main database away from Redis and to MongoDB.

    I won't discuss the politics here but we can't afford to keep all our
    users, posts and comments data inside Redis if the site ever got big. We
    chose MongoDB so we didn't have to change the way we work. This also makes
    it easier for others to trust that this data is safe. Redis can be tricky
    to do correctly.

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
