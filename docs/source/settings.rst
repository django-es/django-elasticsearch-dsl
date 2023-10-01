Settings
########


ELASTICSEARCH_DSL_AUTOSYNC
==========================

Default: ``True``

Set to ``False`` to globally disable auto-syncing.

ELASTICSEARCH_DSL_INDEX_SETTINGS
================================

Default: ``{}``

Additional options passed to the elasticsearch-dsl Index settings (like ``number_of_replicas`` or ``number_of_shards``).

ELASTICSEARCH_DSL_AUTO_REFRESH
==============================

Default: ``True``

Set to ``False`` not force an `index refresh <https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-refresh.html>`_ with every save.

ELASTICSEARCH_DSL_SIGNAL_PROCESSOR
==================================

This (optional) setting controls what SignalProcessor class is used to handle
Django's signals and keep the search index up-to-date.

An example:

.. code-block:: python

    ELASTICSEARCH_DSL_SIGNAL_PROCESSOR = 'django_elasticsearch_dsl.signals.RealTimeSignalProcessor'

Defaults to ``django_elasticsearch_dsl.signals.RealTimeSignalProcessor``.

Options: ``django_elasticsearch_dsl.signals.RealTimeSignalProcessor`` \ ``django_elasticsearch_dsl.signals.CelerySignalProcessor``

In this ``CelerySignalProcessor`` implementation,
Create and update operations will record the updated data primary key from the database and delay the time to find the association to ensure eventual consistency.
Delete operations are processed to obtain associated data before database records are deleted.
And celery needs to be pre-configured in the django project, for example  `Using Celery with Django <https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html>`.

You could, for instance, make a ``CustomSignalProcessor`` which would apply
update jobs as your wish.

ELASTICSEARCH_DSL_PARALLEL
==========================

Default: ``False``

Run indexing (populate and rebuild) in parallel using ES' parallel_bulk() method.
Note that some databases (e.g. sqlite) do not play well with this option.
