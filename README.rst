========================
Django Elasticsearch DSL
========================

.. image:: https://travis-ci.org/sabricot/django-elasticsearch-dsl.png?branch=master
    :target: https://travis-ci.org/sabricot/django-elasticsearch-dsl
.. image:: https://codecov.io/gh/sabricot/django-elasticsearch-dsl/coverage.svg?branch=master
    :target: https://codecov.io/gh/sabricot/django-elasticsearch-dsl
.. image:: https://badge.fury.io/py/django-elasticsearch-dsl.svg
    :target: https://pypi.python.org/pypi/django-elasticsearch-dsl
.. image:: https://readthedocs.org/projects/pip/badge/?version=latest&style=flat
    :target: https://django-elasticsearch-dsl.readthedocs.io/en/latest/

Django Elasticsearch DSL is a package that allows indexing of django models in elasticsearch.
It is built as a thin wrapper around elasticsearch-dsl-py_
so you can use all the features developed by the elasticsearch-dsl-py team.

You can view the full documentation at https://django-elasticsearch-dsl.readthedocs.io

.. _elasticsearch-dsl-py: https://github.com/elastic/elasticsearch-dsl-py

Features
--------

- Based on elasticsearch-dsl-py_ so you can make queries with the Search_ class.
- Django signal receivers on save and delete for keeping Elasticsearch in sync.
- Management commands for creating, deleting, rebuilding and populating indices.
- Elasticsearch auto mapping from django models fields.
- Complex field type support (ObjectField, NestedField).
- Index fast using `parallel` indexing.
- Requirements

   - Django >= 1.11
   - Python 2.7, 3.5, 3.6, 3.7

**Elasticsearch Compatibility:**
The library is compatible with all Elasticsearch versions since 5.x
**but you have to use a matching major version:**

- For Elasticsearch 7.0 and later, use the major version 7 (7.x.y) of the library.

- For Elasticsearch 6.0 and later, use the major version 6 (6.x.y) of the library.

- For Elasticsearch 5.0 and later, use the major version 0.5 (0.5.x) of the library.

.. code-block:: python

    # Elasticsearch 7.x
    elasticsearch-dsl>=7.0.0,<8.0.0

    # Elasticsearch 6.x
    elasticsearch-dsl>=6.0.0,<7.0.0

    # Elasticsearch 5.x
    elasticsearch-dsl>=0.5.1,<6.0.0

.. _Search: http://elasticsearch-dsl.readthedocs.io/en/stable/search_dsl.html
