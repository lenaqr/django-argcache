import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-argcache',
    version='0.1',
    license='AGPLv3',
    description='A function-level caching and invalidaton framework for Django.',
    long_description=README,
    url='https://github.com/luac/django-argcache/',
    author='Anthony Lu',
    author_email='lua@mit.edu',
    packages=[
        'argcache',
        'argcache.extras',
    ],
    package_dir={
        'argcache': 'src'
    },
    include_package_data=True,
    install_requires=[
        'django>=1.7',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
)
