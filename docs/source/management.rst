Management Commands
###################

Delete all indices in Elasticsearch, only the indices associate with a model (``--models``),
or the specific indices by their names (``--indices``):

.. note:: The ``--models`` and ``--indices`` options are mutually exclusive, meaning that you
    can only use one or the other, but not both at the same time.

::

    $ search_index --delete [-f] [--models [app[.model] app[.model] ...]] [--indices index_name [index_name ...]]


Create the indices and their mapping in Elasticsearch:

::

    $ search_index --create [--models [app[.model] app[.model] ...]] [--indices index_name [index_name ...]]

Populate the Elasticsearch mappings with the django models data (index need to be existing):

::

    $ search_index --populate [--models [app[.model] app[.model] ...]] [--indices index_name [index_name ...]] [--parallel] 

Recreate and repopulate the indices:

::

    $ search_index --rebuild [-f] [--models [app[.model] app[.model] ...]] [--indices index_name [index_name ...]] [--parallel] 

