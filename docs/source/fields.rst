Fields
######

Once again the ``django_elasticsearch_dsl.fields`` are subclasses of elasticsearch-dsl-py
fields_. They just add support for retrieving data from django models.


.. _fields: http://elasticsearch-dsl.readthedocs.io/en/stable/persistence.html#mappings

Using Different Attributes for Model Fields
===========================================

Let's say you don't want to store the type of the car as an integer, but as the
corresponding string instead. You need some way to convert the type field on
the model to a string, so we'll just add a method for it:

.. code-block:: python

    # models.py

    class Car(models.Model):
        # ... #
        def type_to_string(self):
            """Convert the type field to its string representation
            (the boneheaded way).
            """
            if self.type == 1:
                return "Sedan"
            elif self.type == 2:
                return "Truck"
            else:
                return "SUV"

Now we need to tell our ``Document`` subclass to use that method instead of just
accessing the ``type`` field on the model directly. Change the CarDocument to look
like this:

.. code-block:: python

    # documents.py

    from django_elasticsearch_dsl import Document, fields

    # ... #

    @registry.register_document
    class CarDocument(Document):
        # add a string field to the Elasticsearch mapping called type, the
        # value of which is derived from the model's type_to_string attribute
        type = fields.TextField(attr="type_to_string")

        class Django:
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
===================

Sometimes, you need to do some extra prepping before a field should be saved to
Elasticsearch. You can add a ``prepare_foo(self, instance)`` method to a Document
(where foo is the name of the field), and that will be called when the field
needs to be saved.

.. code-block:: python

    # documents.py

    # ... #

    class CarDocument(Document):
        # ... #

        foo = TextField()

        def prepare_foo(self, instance):
            return " ".join(instance.foos)

Handle relationship with NestedField/ObjectField
================================================

For example for a model with ForeignKey relationships.

.. code-block:: python

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
        car = models.ForeignKey('Car', related_name='ads')


You can use an ObjectField or a NestedField.

.. code-block:: python

    # documents.py

    from django_elasticsearch_dsl import Document, fields
    from .models import Car, Manufacturer, Ad

    @registry.register_document
    class CarDocument(Document):
        manufacturer = fields.ObjectField(properties={
            'name': fields.TextField(),
            'country_code': fields.TextField(),
        })
        ads = fields.NestedField(properties={
            'description': fields.TextField(analyzer=html_strip),
            'title': fields.TextField(),
            'pk': fields.IntegerField(),
        })

        class Index:
            name = 'cars'

        class Django:
            model = Car
            fields = [
                'name',
                'color',
            ]
            related_models = [Manufacturer, Ad]  # Optional: to ensure the Car will be re-saved when Manufacturer or Ad is updated

        def get_queryset(self):
            """Not mandatory but to improve performance we can select related in one sql request"""
            return super(CarDocument, self).get_queryset().select_related(
                'manufacturer'
            )

        def get_instances_from_related(self, related_instance):
            """If related_models is set, define how to retrieve the Car instance(s) from the related model.
            The related_models option should be used with caution because it can lead in the index
            to the updating of a lot of items.
            """
            if isinstance(related_instance, Manufacturer):
                return related_instance.car_set.all()
            elif isinstance(related_instance, Ad):
                return related_instance.car


Field Classes
=============

Most Elasticsearch field types_ are supported. The ``attr`` argument is a dotted
"attribute path" which will be looked up on the model using Django template
semantics (dict lookup, attribute lookup, list index lookup). By default the attr
argument is set to the field name.

For the rest, the field properties are the same as elasticsearch-dsl
fields_.

So for example you can use a custom analyzer_:

.. _analyzer: http://elasticsearch-dsl.readthedocs.io/en/stable/persistence.html#analysis
.. _types: https://www.elastic.co/guide/en/elasticsearch/reference/5.4/mapping-types.html

.. code-block:: python

    # documents.py

    # ... #

    html_strip = analyzer(
        'html_strip',
        tokenizer="standard",
        filter=["lowercase", "stop", "snowball"],
        char_filter=["html_strip"]
    )

    @registry.register_document
    class CarDocument(Document):
        description = fields.TextField(
            analyzer=html_strip,
            fields={'raw': fields.KeywordField()}
        )

        class Django:
            model = Car
            fields = [
                'name',
                'color',
            ]


Available Fields
================

- Simple Fields

  - ``BooleanField(attr=None, **elasticsearch_properties)``
  - ``ByteField(attr=None, **elasticsearch_properties)``
  - ``CompletionField(attr=None, **elasticsearch_properties)``
  - ``DateField(attr=None, **elasticsearch_properties)``
  - ``DoubleField(attr=None, **elasticsearch_properties)``
  - ``FileField(attr=None, **elasticsearch_properties)``
  - ``FloatField(attr=None, **elasticsearch_properties)``
  - ``IntegerField(attr=None, **elasticsearch_properties)``
  - ``IpField(attr=None, **elasticsearch_properties)``
  - ``KeywordField(attr=None, **elasticsearch_properties)``
  - ``GeoPointField(attr=None, **elasticsearch_properties)``
  - ``GeoShapeField(attr=None, **elasticsearch_properties)``
  - ``ShortField(attr=None, **elasticsearch_properties)``
  - ``TextField(attr=None, **elasticsearch_properties)``

- Complex Fields

  - ``ObjectField(properties, attr=None, **elasticsearch_properties)``
  - ``NestedField(properties, attr=None, **elasticsearch_properties)``

``properties`` is a dict where the key is a field name, and the value is a field
instance.


Document id
===========

The elasticsearch document id (``_id``) is not strictly speaking a field, as it is not 
part of the document itself. The default behavior of ``django_elasticsearch_dsl``
is to use the primary key of the model as the document's id (``pk`` or ``id``).
Nevertheless, it can sometimes be useful to change this default behavior. For this, one
can redefine the ``generate_id(cls, instance)`` class method of the ``Document`` class.

For example, to use an article's slug as the elasticsearch ``_id`` instead of the 
article's integer id, one could use:

.. code-block:: python

    # models.py

    from django.db import models

    class Article(models.Model):
        # ... #

        slug = models.SlugField(
            max_length=255,
            unique=True,
        )

        # ... #


    # documents.py

    from .models import Article

    class ArticleDocument(Document):
        class Django:
            model = Article

        # ... #

        @classmethod
        def generate_id(cls, article):
            return article.slug
