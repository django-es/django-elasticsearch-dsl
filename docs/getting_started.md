# Getting started

## Installation

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
    'test': {
        'hosts': 'localhost:9201'
    },
}
```

`OPENSEARCH_DSL` is then passed
to [`opensearch_dsl.connections.configure`](http://elasticsearch-dsl.readthedocs.io/en/stable/configuration.html#multiple-clusters)
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

First create a subclass of [`django_opensearch_dsl.Document`](/document/) containing the subclasses `Index`
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
        # Paginate the Django queryset used to populate the index with the specified size
        # This per-Document setting overrides settings.OPENSEARCH_DSL_QUERYSET_PAGINATION.
        queryset_pagination = 5000
```

## Create and Populate Opensearch's Indices

To create indices, use the `opensearch index` management command :

* `python manage.py opensearch index create`

and to populate the indices, use the `opensearch document` management command :

* `python3 manage.py opensearch document index`

See [management commands](/management/) for more information.

## Search

To get
an `opensearch-dsl` [`Search`](https://elasticsearch-dsl.readthedocs.io/en/latest/search_dsl.html#the-search-object)
instance, use:

```python
s = CarDocument.search().filter("term", color="red")

# or

s = CarDocument.search().query("match", description="beautiful")

for hit in s:
    print("Car name : {}, description {}".format(hit.name, hit.description))
```

The previous example returns a result specific
to [`opensearch-dsl`](http://elasticsearch-dsl.readthedocs.io/en/latest/search_dsl.html#response), but it is also
possible to convert the opensearch result into a real Django queryset, just be aware that this costs a SQL request to
retrieve the model instances with the ids returned by the opensearch query.


```python
s = CarDocument.search().filter("term", color="blue")[:30]
qs = s.to_queryset()
# qs is just a django queryset and it is called with order_by to keep
# the same order as the opensearch result.
for car in qs:
    print(car.name)
```
