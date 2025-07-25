========================
Django Elasticsearch DSL
========================

.. image:: https://github.com/django-es/django-elasticsearch-dsl/actions/workflows/ci.yml/badge.svg
    :target: https://github.com/django-es/django-elasticsearch-dsl/actions/workflows/ci.yml
.. image:: https://codecov.io/gh/django-es/django-elasticsearch-dsl/coverage.svg?branch=master
    :target: https://codecov.io/gh/django-es/django-elasticsearch-dsl
.. image:: https://badge.fury.io/py/django-elasticsearch-dsl.svg
    :target: https://pypi.python.org/pypi/django-elasticsearch-dsl
.. image:: https://readthedocs.org/projects/django-elasticsearch-dsl/badge/?version=latest&style=flat
    :target: https://django-elasticsearch-dsl.readthedocs.io/en/latest/

Django Elasticsearch DSL is a package that allows indexing of django models in elasticsearch.
It is built as a thin wrapper around elasticsearch-py_
so you can use all the features developed by the elasticsearch-py team.

You can view the full documentation at https://django-elasticsearch-dsl.readthedocs.io

.. _elasticsearch-py: https://github.com/elastic/elasticsearch-py

Features
--------

- Based on elasticsearch-py_ so you can make queries with the Search_ class.
- Django signal receivers on save and delete for keeping Elasticsearch in sync.
- Management commands for creating, deleting, rebuilding and populating indices.
- Elasticsearch auto mapping from django models fields.
- Complex field type support (ObjectField, NestedField).
- Index fast using `parallel` indexing.
- Requirements

   - Django >= 4.2
   - Python 3.9, 3.10, 3.11, 3.12, 3.13

**Elasticsearch Compatibility:**
The library is compatible with all Elasticsearch versions since 5.x
**but you have to use a matching major version:**

- For Elasticsearch 9.0 and later, use the major version 9 (9.x.y) of the library.

- For Elasticsearch 8.0 and later, use the major version 8 (8.x.y) of the library.

- For Elasticsearch 7.0 and later, use the major version 7 (7.x.y) of the library.

- For Elasticsearch 6.0 and later, use the major version 6 (6.x.y) of the library.

.. code-block:: python

    # Elasticsearch 9.x
    elasticsearch>=9.0.0,<10.0.0

    # Elasticsearch 8.x
    elasticsearch-dsl>=8.0.0,<9.0.0

    # Elasticsearch 7.x
    elasticsearch-dsl>=7.0.0,<8.0.0

    # Elasticsearch 6.x
    elasticsearch-dsl>=6.0.0,<7.0.0

.. _Search: http://elasticsearch-dsl.readthedocs.io/en/stable/search_dsl.html
