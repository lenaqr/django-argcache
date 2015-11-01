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
