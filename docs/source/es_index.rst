Index
#####

In typical scenario using `class Index` on a `Document` class is sufficient to perform any action.
In a few cases though it can be useful to manipulate an Index object directly.

To define an Elasticsearch index you must instantiate a ``elasticsearch_dsl.Index`` class
and set the name and settings of the index.
After you instantiate your class,
you need to associate it with the Document you want to put in this Elasticsearch index
and also add the `registry.register_document` decorator.


.. code-block:: python

    # documents.py
    from elasticsearch_dsl import Index
    from django_elasticsearch_dsl import Document
    from .models import Car, Manufacturer

    # The name of your index
    car = Index('cars')
    # See Elasticsearch Indices API reference for available settings
    car.settings(
        number_of_shards=1,
        number_of_replicas=0
    )

    @registry.register_document
    @car.document
    class CarDocument(Document):
        class Django:
            model = Car
            fields = [
                'name',
                'color',
            ]

    @registry.register_document
    class ManufacturerDocument(Document):
        class Index:
            name = 'manufacture'
            settings = {'number_of_shards': 1,
                        'number_of_replicas': 0}

        class Django:
            model = Manufacturer
            fields = [
                'name',
                'country_code',
            ]

When you execute the command::

    $ ./manage.py search_index --rebuild

This will create two index named ``cars`` and ``manufacture``
in Elasticsearch with appropriate mapping.

** If your model have huge amount of data, its preferred to use `parallel` indexing.
To do that, you can pass `--parallel` flag while reindexing or populating.
**


Signals
=======

* ``django_elasticsearch_dsl.signals.post_index``
    Sent after document indexing is completed. (not applicable for ``parallel`` indexing).
    Provides the following arguments:

    ``sender``
        A subclass of ``django_elasticsearch_dsl.documents.DocType`` used
        to perform indexing.

    ``instance``
        A ``django_elasticsearch_dsl.documents.DocType`` subclass instance.

    ``actions``
        A generator containing document data that were sent to elasticsearch for indexing.

    ``response``
        The response from ``bulk()`` function of ``elasticsearch-py``,
        which includes ``success`` count and ``failed`` count or ``error`` list.
