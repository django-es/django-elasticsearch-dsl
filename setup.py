#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = '8.2'

if sys.argv[-1] == 'publish':
    try:
        import wheel
        print("Wheel version: ", wheel.__version__)
    except ImportError:
        print('Wheel library missing. Please run "pip install wheel"')
        sys.exit()
    os.system('python setup.py sdist upload')
    os.system('python setup.py bdist_wheel upload')
    sys.exit()

if sys.argv[-1] == 'tag':
    print("Tagging the version on git:")
    os.system("git tag -a %s -m 'version %s'" % (version, version))
    os.system("git push --tags")
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='django-elasticsearch-dsl',
    version=version,
    python_requires=">=3.9",
    description="""Wrapper around elasticsearch-dsl-py for django models""",
    long_description=readme + '\n\n' + history,
    author='Sabricot',
    url='https://github.com/sabricot/django-elasticsearch-dsl',
    packages=[
        'django_elasticsearch_dsl',
    ],
    include_package_data=True,
    install_requires=[
        'elasticsearch>=9.0.0,<10.0.0',
        'six',
    ],
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords='django elasticsearch elasticsearch-dsl',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Framework :: Django :: 4.2',
        'Framework :: Django :: 5.0',
        'Framework :: Django :: 5.1',
        'Framework :: Django :: 5.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
    extras_require={
        'celery':  ["celery>=5.5.3"],
    }
)
