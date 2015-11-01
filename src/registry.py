
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

from django.conf import settings

__all__ = ['register_cache', 'dump_all_caches', 'caches_locked']

all_caches = []

def register_cache(cache_obj):
    all_caches.append(cache_obj)

def dump_all_caches():
    for c in all_caches:
        c.delete_all()

def _finalize_caches():
    from argcache.queued import do_all_pending
    do_all_pending()
    if settings.CACHE_DEBUG:
        print "Initialized caches"

_caches_locked = False
def caches_locked():
    return _caches_locked

def _lock_caches():
    global _caches_locked
    _caches_locked = True
