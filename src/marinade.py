""" Converts a set of arguments to a string """
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

import inspect

from django.db.models import Model
from django.db.models.query import QuerySet

from .utils import force_str

def describe_class(cls):
    return '%s.%s' % (cls.__module__.rstrip('.'), cls.__name__)

def get_containing_class():
    # intended to be called from a method decorator's body
    # get_containg_class -> decorator -> containing class/module
    class_name = inspect.currentframe().f_back.f_back.f_code.co_name
    if class_name == '<module>':
        return None
    return class_name

def describe_func(func, class_name=None):
    if hasattr(func, 'im_class'):
        # I don't think we actually hit this case... this is only for bound/unbound member functions
        return '%s.%s' % (describe_class(func.im_class), func.__name__)
    else:
        if class_name is None:
            return '%s.%s' % (func.__module__.rstrip('.'), func.__name__)
        else:
            return '%s.%s.%s' % (func.__module__.rstrip('.'), class_name, func.__name__)

# It's kinda like pickling, but not quite
def marinade_dish(arg):
    if isinstance(arg, QuerySet):
        return marinade_dish(list(arg))
    if isinstance(arg, list):
        return '[%s]' % ','.join([marinade_dish(item) for item in arg])
    if isinstance(arg, Model):
        if arg.id is None:
            import random
            # TODO: Make this log something
            print "PASSING UNSAVED MODEL!!! ERROR!!! CACHING CODE SHOULD NOT BE ENABLED!!!"
            # Do the right thing anyway
            return str(random.randint(0,999999))
        return str(arg.id)
    if isinstance(arg, type):
        return describe_class(arg)
    if hasattr(arg, '__marinade__'):
        return arg.__marinade__()
    return force_str(arg)
