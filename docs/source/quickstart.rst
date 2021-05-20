
Quickstart
##########

Install and configure
=====================

Install Django Elasticsearch DSL::

    pip install django-elasticsearch-dsl


Then add ``django_elasticsearch_dsl`` to the INSTALLED_APPS

You must define ``ELASTICSEARCH_DSL`` in your django settings.

For example:

.. code-block:: python

    ELASTICSEARCH_DSL={
        'default': {
            'hosts': 'localhost:9200'
        },
    }

``ELASTICSEARCH_DSL`` is then passed to ``elasticsearch-dsl-py.connections.configure`` (see here_).

.. _here: http://elasticsearch-dsl.readthedocs.io/en/stable/configuration.html#multiple-clusters

Declare data to index
=====================

Then for a model:

.. code-block:: python

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

To make this model work with Elasticsearch,
create a subclass of ``django_elasticsearch_dsl.Document``,
create a ``class Index`` inside the ``Document`` class
to define your Elasticsearch indices, names, settings etc
and at last register the class using ``registry.register_document`` decorator.
It is required to define ``Document`` class in  ``documents.py`` in your app directory.

.. code-block:: python

    # documents.py

    from django_elasticsearch_dsl import Document
    from django_elasticsearch_dsl.registries import registry
    from .models import Car


    @registry.register_document
    class CarDocument(Document):
        class Index:
            # Name of the Elasticsearch index
            name = 'cars'
            # See Elasticsearch Indices API reference for available settings
            settings = {'number_of_shards': 1,
                        'number_of_replicas': 0}

        class Django:
            model = Car # The model associated with this Document

            # The fields of the model you want to be indexed in Elasticsearch
            fields = [
                'name',
                'color',
                'description',
                'type',
            ]

            # Ignore auto updating of Elasticsearch when a model is saved
            # or deleted:
            # ignore_signals = True

            # Configure how the index should be refreshed after an update.
            # See Elasticsearch documentation for supported options:
            # https://www.elastic.co/guide/en/elasticsearch/reference/master/docs-refresh.html
            # This per-Document setting overrides settings.ELASTICSEARCH_DSL_AUTO_REFRESH.
            # auto_refresh = False

            # Paginate the django queryset used to populate the index with the specified size
            # (by default it uses the database driver's default setting)
            # queryset_pagination = 5000

Populate
========

To create and populate the Elasticsearch index and mapping use the search_index command::

    $ ./manage.py search_index --rebuild

Now, when you do something like:

.. code-block:: python

    car = Car(
        name="Car one",
        color="red",
        type=1,
        description="A beautiful car"
    )
    car.save()

The object will be saved in Elasticsearch too (using a signal handler).

Search
======

To get an elasticsearch-dsl-py Search_ instance, use:

.. code-block:: python

    s = CarDocument.search().filter("term", color="red")

    # or

    s = CarDocument.search().query("match", description="beautiful")

    for hit in s:
        print(
            "Car name : {}, description {}".format(hit.name, hit.description)
        )

The previous example returns a result specific to elasticsearch_dsl_,
but it is also possible to convert the elastisearch result into a real django queryset,
just be aware that this costs a sql request to retrieve the model instances
with the ids returned by the elastisearch query.

.. _Search: https://elasticsearch-dsl.readthedocs.io/en/latest/search_dsl.html#the-search-object
.. _elasticsearch_dsl: http://elasticsearch-dsl.readthedocs.io/en/latest/search_dsl.html#response

.. code-block:: python

    s = CarDocument.search().filter("term", color="blue")[:30]
    qs = s.to_queryset()
    # qs is just a django queryset and it is called with order_by to keep
    # the same order as the elasticsearch result.
    for car in qs:
        print(car.name)
