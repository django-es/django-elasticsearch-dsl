=============================
Django Elasticsearch DSL
=============================

.. image:: https://travis-ci.org/sabricot/django-elasticsearch-dsl.png?branch=master
    :target: https://travis-ci.org/sabricot/django-elasticsearch-dsl
.. image:: https://codecov.io/gh/sabricot/django-elasticsearch-dsl/coverage.svg?branch=master
    :target: https://codecov.io/gh/sabricot/django-elasticsearch-dsl

This is a package that allows indexing of django models in elasticsearch. It is
built as a tin wrapper around elasticsearch-dsl-py_ so you can use all the features developed
by the elasticsearch-dsl-py team.

.. _elasticsearch-dsl-py: https://github.com/elastic/elasticsearch-dsl-py

Features
--------

- Based on elasticsearch-dsl-py_ so you can make query with the Search_ class.
- Django signal receivers on save and delete for keeping Elasticsearch in sync.
- Management commands for create, delete, rebuild indices and populate them.
- Elasticsearch auto mapping from django models fields.
- Complex field type support (ObjectField, NestedField).
- Requirements
   - Django >= 1.8
   - Python 2.7, 3.4, 3.5
   - Elasticsearch >= 2.1

.. _Search: http://elasticsearch-dsl.readthedocs.io/en/stable/search_dsl.html

Quickstart
----------

Install Django Elasticsearch DSL

Then add ``django_elasticsearch_dsl`` to the INSTALLED_APPS

You must define ``ELASTICSEARCH_DSL`` in your django settings.

For example

.. code:: python

    ELASTICSEARCH_DSL={
        'default': {
            'hosts': 'localhost:9200'
        },
    }

``ELASTICSEARCH_DSL`` is then pass to ``elasticsearch-dsl-py.connections.configure`` (see here_).

.. _here: http://elasticsearch-dsl.readthedocs.io/en/stable/configuration.html#multiple-clusters

Then for a model

.. code:: python

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

To make this model work with Elasticsearch, create a subclass of ``django_elasticsearch_dsl.DocType``.
And create a ``django_elasticsearch_dsl.Index`` to define your Elasticsearch indices names and settings. This classes must be
define in a ``documents.py`` file.

.. code:: python

    # documents.py

    from django_elasticsearch_dsl import DocType, Index
    from .models import Car

    # Name of the Elasticsearch index
    car = Index('cars')
    # See Elasticsearch Indices API reference for available settings
    car.settings(
        number_of_shards=1,
        number_of_replicas=0
    )


    @car.doc_type
    class CarDocument(DocType):
        class Meta:
            model = Car # The model associate with this DocType
            fields = [
                'name',
                'color',
                'description',
                'type',
            ] # the fields of the model you want to be indexed in Elasticsearch

            # ignore_signals = True # To ignore auto updating of Elasticsearch when a model is save or delete


To create and populate the Elasticsearch index and mapping use the search_index command::

    $ ./manage.py search_index --rebuild

Now, when you do something like:

.. code:: python

    car = Car(name="Car one", color="red", type=1, description="A beautiful car")
    car.save()

The object will be saved in Elasticsearch too (using a signal handler). To get a
elasticsearch-dsl-py Search_ instance, use:

.. code:: python

    s = CarDocument.search().filter("term", color="red")

    # or

    s = CarDocument.search().query("match", description="beautiful")

    for hit in s:
        print("Car name : {}, description {}".format(hit.name, hit.description))

Fields
------

Once again the ``django_elasticsearch_dsl.fields`` are subclasses of elasticsearch-dsl-py
fields_. They just add support for retrieving data from django models.


.. _fields: http://elasticsearch-dsl.readthedocs.io/en/stable/persistence.html#mappings

Using Different Attributes for Model Fields
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's say you don't want to store the type of the car as an integer, but as the
corresponding string instead. You need some way to convert the type field on
the model to a string, so we'll just add a method for it:

.. code:: python

    # models.py

    class Car(models.Model):
        # ... #
        def type_to_string(self):
            """Convert the type field to its string representation (the boneheaded way)"""
            if self.type == 1:
                return "Sedan"
            elif self.type == 2:
                return "Truck"
            else:
                return "SUV"

Now we need to tell our ``DocType`` subclass to use that method instead of just
accessing the ``type`` field on the model directly. Change the CarDocument to look
like this:

.. code:: python

    # documents.py

    from django_elasticsearch_dsl import DocType, fields

    # ... #

    @car.doc_type
    class CarDocument(DocType):
        # add a string field to the Elasticsearch mapping called type, the value of
        # which is derived from the model's type_to_string attribute
        type = fields.StringField(attr="type_to_string")

        class Meta:
            model = Car
            # we removed the type field from here
            fields = [
                'name',
                'color',
                'description',
            ]

After a change like this we need to rebuild the index with::

    $ ./manage.py search_index --rebuild

Using prepare_field
~~~~~~~~~~~~~~~~~~~

Sometimes, you need to do some extra prepping before a field should be saved to
elasticsearch. You can add a ``prepare_foo(self, instance)`` method to a DocType
(where foo is the name of the field), and that will be called when the field
needs to be saved.

.. code:: python

    # documents.py

    # ... #

    class CarDocument(DocType):
        # ... #

        foo = StringField()

        def prepare_foo(self, instance):
            return " ".join(instance.foos)

Handle relationship with NestedField/ObjecField
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For example for a model with ForeignKey relationships.

.. code:: python

    # models.py

    class Car(models.Model):
        name = models.CharField()
        color = models.CharField()
        manufacturer = models.ForeignKey('Manufacturer')

    class Manufacturer(models.Model):
        name = models.CharField()
        country_code = models.CharField(max_length=2)
        created = models.DateField()

    class Ad(models.Model):
        title = models.CharField()
        description = models.TextField()
        created = models.DateField(auto_now_add=True)
        modified = models.DateField(auto_now=True)
        url = models.URLField()
        car = models.ForeignKey('Car')

        # This function will be called by the ads NestedField from the CarDocument
        def ads(self):
            return self.ad_set.all()


You can use an ObjecField or NestedField.

.. code:: python

    # documents.py

    from django_elasticsearch_dsl import DocType, Index
    from .models import Car

    car = Index('cars')
    car.settings(
        number_of_shards=1,
        number_of_replicas=0
    )


    @car.doc_type
    class CarDocument(DocType):
        manufacturer = fields.ObjectField(properties={
            'name': fields.StringField(),
            'country_code': fields.StringField(),
        })
        ads = fields.NestedField(properties={
            'description': fields.StringField(analyzer=html_strip),
            'title': fields.StringField(),
            'pk': fields.IntegerField(),
        })

        class Meta:
            model = Car
            fields = [
                'name',
                'color',
            ]

        # Not mandadory but to improve performance we can select related in one sql request
        def get_queryset(self):
            return super(CarDocument, self).get_queryset().select_related(
                'manufacturer')

Field Classes
~~~~~~~~~~~~~
Most elasticsearch field types_ are supported. The ``attr`` argument is a dotted
"attribute path" which will be looked up on the model using Django template
semantics (dict lookup, attribute lookup, list index lookup). By default the attr
argument is set to the field name.

For the rest, the field properties are the same as elasticsearch-dsl-py
fields_.

So for example you can use a custom analyzer_:

.. _analyzer: http://elasticsearch-dsl.readthedocs.io/en/stable/persistence.html#analysis
.. _types: https://www.elastic.co/guide/en/elasticsearch/reference/2.3/mapping-types.html

.. code:: python

    # documents.py

    # ... #

    html_strip = analyzer(
        'html_strip',
        tokenizer="standard",
        filter=["standard", "lowercase", "stop", "snowball"],
        char_filter=["html_strip"]
    )

    @car.doc_type
    class CarDocument(DocType):
        description = fields.StringField(
            analyzer=html_strip,
            fields={'raw': fields.StringField(index='not_analyzed')}
        )

        class Meta:
            model = Car
            fields = [
                'name',
                'color',
            ]


Available Fields
~~~~~~~~~~~~~~~~

- Simple Fields

    - StringField(attr=None, \*\*elasticsearch_properties)
    - FloatField(attr=None, \*\*elasticsearch_properties)
    - DoubleField(attr=None, \*\*elasticsearch_properties)
    - ByteField(attr=None, \*\*elasticsearch_properties)
    - ShortField(attr=None, \*\*elasticsearch_properties)
    - IntegerField(attr=None, \*\*elasticsearch_properties)
    - DateField(attr=None, \*\*elasticsearch_properties)
    - BooleanField(attr=None, \*\*elasticsearch_properties)
    - GeoPointField(attr=None, \*\*elasticsearch_properties)
    - GeoShapField(attr=None, \*\*elasticsearch_properties)
    - IpField(attr=None, \*\*elasticsearch_properties)
    - CompletionField(attr=None, \*\*elasticsearch_properties)

- Complex Fields

    - ObjectField(properties, attr=None, \*\*elasticsearch_properties)
    - NestedField(properties, attr=None, \*\*elasticsearch_properties)

``properties`` is a dict where the key is a field name, and the value is a field
instance.


Index
-----

To define an Elasticsearch index you must instantiate a ``django_elasticsearch_dsl.Index`` class for set the name
and settings of the index. This class inherit form elasticsearch-dsl-py Index_.
After you instantiate your class you need to associate it with the DocType you
want to put in this Elasticsearch index.


.. _Index: http://elasticsearch-dsl.readthedocs.io/en/stable/persistence.html#index

.. code:: python

    # documents.py

    from django_elasticsearch_dsl import DocType, Index
    from .models import Car, Manufacturer

    # The name of your index
    car = Index('cars')
    # See Elasticsearch Indices API reference for available settings
    car.settings(
        number_of_shards=1,
        number_of_replicas=0
    )


    @car.doc_type
    class CarDocument(DocType):
        class Meta:
            model = Car
            fields = [
                'name',
                'color',
            ]

    @car.doc_type
    class ManufacturerDocument(DocType):
        class Meta:
            model = Car
            fields = [
                'name', # If a field as the same name in multiple DocType of the same Index,
                        # the field type must be identical (here fields.StringField)
                'country_code',
            ]

When you execute the command::

    $ ./manage.py search_index --rebuild

This will create an index named ``cars`` in elasticsearch with two mapping
``manufacturer_document`` and ``car_document``.


Management Commands
-------------------

To delete all indices in Elasticsearch or only the indices associate with a model (--models):

::

    $ search_index --delete [-f] [--models [app[.model] app[.model] ...]]


To create the indices and their mapping in Elasticsearch

::

    $ search_index --create [--models [app[.model] app[.model] ...]]

To populate the Elasticsearch mappings with the django models data (index need to be existing)

::

    $ search_index --populate [--models [app[.model] app[.model] ...]]

To recreate and repopulate the indices you can use:

::

    $ search_index --rebuild [-f] [--models [app[.model] app[.model] ...]]


Testing
-------

You can run the tests by creating a Python virtual environment, installing
the requirements from ``requirements_test.txt`` (``pip install -r requirements_test``)
and running ``python runtests.py`` or ``make test`` (``make test-all`` for tox testing)


TODO
----

- Add support for --using (use another elasticsearch cluster) in management commands.
- Add management commands for mapping level operations (like update_mapping....).
- Dedicated documentation.
- Generate ObjecField/NestField propeties from a DocType class.
- Add possibility to set a default index in ``DocType: class Meta index = 'cars'``.
- More examples and integration tests.
- Better ``ESTestCase`` and documentation for testing

