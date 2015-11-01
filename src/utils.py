__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of ArgCache.
Copyright (c) 2015 by the individual contributors
  (see AUTHORS file)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

def force_str(x):
    """
    Forces x to a str, encoding via utf8 if needed.

    >>> force_str('\\xc3\\x85ngstrom')
    '\\xc3\\x85ngstrom'
    >>> force_str(u'\\xc5ngstrom')
    '\\xc3\\x85ngstrom'

    """
    if isinstance(x, str):
        return x
    return unicode(x).encode('utf8')
