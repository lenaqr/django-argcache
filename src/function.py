""" Decorator to automatically add a cache to a function. """
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

import functools
import inspect
import types

from .argcache import ArgCache
from .marinade import describe_func, get_containing_class

class ArgCacheDecorator(ArgCache):
    """ An ArgCache that gets its parameters from a function. """

    def __new__(cls, func_or_spec=None, spec=None, **kwargs):
        ## This __new__ method exists to allow the decorator to be
        ## called in a couple of different ways. In particular, it is
        ## possible to pass a list of "cache directives" (typically a
        ## sequence of depend_on_foo calls) which will be applied to
        ## the cached function after it is made.
        if isinstance(func_or_spec, list):
            # Invoked as cache_function([list of cache directives])
            if spec is not None:
                raise TypeError(
                    "cache_function() got multiple values for keyword argument 'spec'")
            return functools.partial(cls, spec=func_or_spec, **kwargs)
        elif func_or_spec is None:
            # Invoked as cache_function(spec=[list of cache directives])
            # or possibly other kwargs like cache_function(timeout_seconds=N)
            return functools.partial(cls, spec=spec, **kwargs)
        else:
            # Actually applying the decorator
            return super(ArgCacheDecorator, cls).__new__(
                cls, func_or_spec, spec=spec, **kwargs)

    def __init__(self, func, spec=None, **kwargs):
        """ Wrap func in a ArgCache. """

        ## Keep the original function's name and docstring
        ## If the original function has any more-complicated attrs,
        ## don't bother to maintain them; we have our own attrs,
        ## and merging custom stuff could be dangerous.
        if hasattr(func, '__name__'):
            self.__name__ = func.__name__
        if hasattr(func, '__doc__'):
            self.__doc__ = func.__doc__

        self.func = func
        containing_class = kwargs.pop('containing_class', get_containing_class())
        extra_name = kwargs.pop('extra_name', '')
        name = describe_func(func, containing_class) + extra_name
        params, varargs, keywords, _ = inspect.getargspec(func)
        if varargs is not None:
            raise ESPError("ArgCache does not support varargs.")
        if keywords is not None:
            raise ESPError("ArgCache does not support keywords.")

        super(ArgCacheDecorator, self).__init__(name=name, params=params, **kwargs)

        # Apply cache directives, if any
        if spec is not None:
            for method in spec:
                method(self)

    # TODO: this signature may break if we have a kwarg named `self`
    # (same applies to __call__ below)
    # for now... assume this doesn't happen
    def arg_list_from(self, *args, **kwargs):
        """ Normalizes arguments to get an arg_list. """
        callargs = inspect.getcallargs(self.func, *args, **kwargs)
        return [callargs[param] for param in self.params]

    def __call__(self, *args, **kwargs):
        """ Call the function, using the cache is possible. """
        use_cache = kwargs.pop('use_cache', True)
        cache_only = kwargs.pop('cache_only', False)

        if use_cache:
            arg_list = self.arg_list_from(*args, **kwargs)
            retVal = self.get(arg_list, default=self.CACHE_NONE)

            if retVal is not self.CACHE_NONE:
                return retVal

            if cache_only:
                retVal = None
            else:
                retVal = self.func(*args, **kwargs)
                self.set(arg_list, retVal)
        else:
            retVal = self.func(*args, **kwargs)

        return retVal

    # make bound member functions work...
    def __get__(self, obj, objtype=None):
        """ Python member functions are such hacks... :-D """
        return types.MethodType(self, obj, objtype)


# This is a bit more of a decorator-style name
cache_function = ArgCacheDecorator

def cache_function_for(timeout_seconds):
    return cache_function(timeout_seconds=timeout_seconds)

# A "directive" is simply a lambda that calls the appropriate method
# on an ArgCache instance.
def directive_maker(method):
    def directive(*args, **kwargs):
        return (lambda cache_obj: method(cache_obj, *args, **kwargs))
    return directive

depend_on_model = directive_maker(ArgCache.depend_on_model)
depend_on_row = directive_maker(ArgCache.depend_on_row)
depend_on_cache = directive_maker(ArgCache.depend_on_cache)
depend_on_m2m = directive_maker(ArgCache.depend_on_m2m)
ensure_token = directive_maker(ArgCache.get_or_create_token)
