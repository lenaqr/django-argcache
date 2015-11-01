
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

from django.apps import AppConfig

class CacheConfig(AppConfig):
    """ Makes sure all caches are inserted. Replacement for cache_loader. """

    name = 'argcache'

    def ready(self):
        import sys
        from django.conf import settings
        from argcache.registry import _finalize_caches, _lock_caches
        from django.apps import apps

        # Make sure everything's already imported

        #Initializing the model cache for customforms
        from esp.customforms.linkfields import cf_cache
        cf_cache._populate()

        # Import views files from INSTALLED_APPS
        for app_config in apps.get_app_configs():
            __import__(app_config.name, {}, {}, ['models'])

        #   Make sure template override cache is registered
        import esp.utils.template

        #   Make sure all cached inclusion tags are registered
        import esp.utils.inclusion_tags

        # import argcache.test

        # Fix up the queued events
        _finalize_caches()
        _lock_caches()
