django-argcache
===============

A Django app that provides function caching and event-driven
invalidation based on explicitly declared dependencies.

Detailed documentation is in the "docs" directory.

Installation
------------

From github:

```
$ git clone git://github.com/luac/django-argcache.git
$ python setup.py install
```

Setup
-----

Add argcache to your INSTALLED_APPS:

```
INSTALLED_APPS = (
    ...
    'argcache.apps.ArgCacheConfig',
)
```

Include the argcache URLconf in your project urls.py:

```
url(r'^cache/', include('argcache.urls')),
```

If your apps define any cached functions that aren't automatically
imported at Django start, create a file named caches.py that imports
them. This is necessary because ArgCache needs to know about all
cached functions so that it can expire them as necessary.
