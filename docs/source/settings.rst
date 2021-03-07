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

You could, for instance, make a ``CelerySignalProcessor`` which would add
update jobs to the queue to for delayed processing.

ELASTICSEARCH_DSL_PARALLEL
==========================

Default: ``False``

Run indexing (populate and rebuild) in parallel using ES' parallel_bulk() method.
Note that some databases (e.g. sqlite) do not play well with this option.
