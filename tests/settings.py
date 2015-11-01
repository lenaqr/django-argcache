import os
TESTS_DIR = os.path.dirname(__file__)

SECRET_KEY = 'abc'

INSTALLED_APPS = [
    'argcache',
    'tests',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(TESTS_DIR, 'db.sqlite3'),
    }
}

ROOT_URLCONF = 'argcache.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'loaders': [
                'django.template.loaders.app_directories.Loader',
                'django.template.loaders.eggs.Loader',
            ]
        }
    }
]
