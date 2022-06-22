Django Opensearch DSL
=====================

[![PyPI Version](https://badge.fury.io/py/django-opensearch-dsl.svg)](https://badge.fury.io/py/django-opensearch-dsl)
[![Documentation Status](https://readthedocs.org/projects/django-opensearch-dsl/badge/?version=latest)](https://django-opensearch-dsl.readthedocs.io/en/latest/?badge=latest)
![Tests](https://github.com/Codoc-os/django-opensearch-dsl/workflows/Tests/badge.svg)
[![Python 3.6+](https://img.shields.io/badge/Python-3.6+-brightgreen.svg)](#)
[![Django 2.1+](https://img.shields.io/badge/Django-2.1+-brightgreen.svg)](#)
[![License Apache 2](https://img.shields.io/badge/license-Apache%202-brightgreen.svg)](https://github.com/Codoc-os/django-opensearch-dsl/blob/master/LICENSE)
[![codecov](https://codecov.io/gh/Codoc-os/django-opensearch-dsl/branch/master/graph/badge.svg)](https://codecov.io/gh/Codoc-os/django-opensearch-dsl)
[![CodeFactor](https://www.codefactor.io/repository/github/Codoc-os/django-opensearch-dsl/badge)](https://www.codefactor.io/repository/github/Codoc-os/django-opensearch-dsl)

**Django Opensearch DSL** is a package that allows the indexing of Django models in opensearch. It is built as a thin
wrapper around [`opensearch-dsl-py`](https://github.com/opensearch-project/opensearch-dsl-py)
so you can use all the features developed by the `opensearch-dsl` team.

You can view the full documentation
at [https://django-opensearch-dsl.readthedocs.io](https://django-opensearch-dsl.readthedocs.io/en/latest/).

## Features

- Based on [`opensearch-dsl-py`](https://github.com/opensearch-project/opensearch-dsl-py) so you can make queries with
  the [`Search`](https://elasticsearch-dsl.readthedocs.io/en/latest/search_dsl.html#the-search-object)
  object.
- Management commands for creating, deleting, and populating indices and documents.
- Opensearch auto mapping from Django models fields.
- Complex field type support (`ObjectField`, `NestedField`).
- Index fast using `parallel` indexing.

## Requirements

* `Python>=3.6`
* `django>=2.1`
* `opensearch-dsl~=1.0.0`
* `python-dateutil~=2.8.2`

## Installation and Configuration

The easiest way to install `django-opensearch-dsl` is through `pip`:

* `pip install django-opensearch-dsl`

Then add `django_opensearch_dsl` to your `INSTALLED_APPS` settings.

You must then define `OPENSEARCH_DSL` in your Django settings.

For example:

```python
OPENSEARCH_DSL = {
    'default': {
        'hosts': 'localhost:9200'
    },
    'secure': {
        'hosts': [{"scheme": "https", "host": "192.30.255.112", "port": 9201}],
        'http_auth': ("admin", "password"),
        'timeout': 120,
    },
}
```

`OPENSEARCH_DSL` is then passed
to [`opensearch_dsl_py.connections.configure`](http://elasticsearch-dsl.readthedocs.io/en/stable/configuration.html#multiple-clusters)
.

## Create Document Classes

To index instances of the following model :

```python
# models.py

class Car(models.Model):
    name = models.CharField()
    color = models.CharField()
    description = models.TextField()
    type = models.IntegerField(choices=[
        (1, "Sedan"),
        (2, "Truck"),
        (4, "SUV"),
    ])
```

First create a subclass of [`django_opensearch_dsl.Document`](document.md) containing the subclasses `Index`
(which define the index' settings) and `Django` (which contains settings related to your django `Model`). Finally,
register the class using `registry.register_document()` decorator.

It is required to define `Document` classes inside a file named `documents.py` in your apps' directory.

```python
# documents.py

from django_opensearch_dsl import Document
from django_opensearch_dsl.registries import registry
from .models import Car


@registry.register_document
class CarDocument(Document):
    class Index:
        name = 'cars'  # Name of the Opensearch index
        settings = {  # See Opensearch Indices API reference for available settings
            'number_of_shards': 1,
            'number_of_replicas': 0
        }
        # Configure how the index should be refreshed after an update.
        # See Opensearch documentation for supported options.
        # This per-Document setting overrides settings.OPENSEARCH_DSL_AUTO_REFRESH.
        auto_refresh = False

    class Django:
        model = Car  # The model associated with this Document        
        fields = [  # The fields of the model you want to be indexed in Opensearch
            'name',
            'color',
            'description',
            'type',
        ]
        # Paginate the django queryset used to populate the index with the specified size
        # This per-Document setting overrides settings.OPENSEARCH_DSL_QUERYSET_PAGINATION.
        queryset_pagination = 5000
```
