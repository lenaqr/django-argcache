import os
TESTS_DIR = os.path.dirname(__file__)

SECRET_KEY = 'abc'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'argcache.apps.ArgCacheConfig',
    'tests',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(TESTS_DIR, 'db.sqlite3'),
    }
}

ROOT_URLCONF = 'argcache.urls'

TEMPLATE_LOADERS = [
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'loaders': TEMPLATE_LOADERS
        }
    }
]

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]
