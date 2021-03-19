Management Commands
###################

Delete all indices in Elasticsearch or only the indices associate with a model (``--models``):

::

    $ search_index --delete [-f] [--models [app[.model] app[.model] ...]]


Create the indices and their mapping in Elasticsearch:

::

    $ search_index --create [--models [app[.model] app[.model] ...]]

Populate the Elasticsearch mappings with the django models data (index need to be existing):

::

    $ search_index --populate [--models [app[.model] app[.model] ...]] [--parallel] [--refresh]

Recreate and repopulate the indices:

::

    $ search_index --rebuild [-f] [--models [app[.model] app[.model] ...]] [--parallel] [--refresh]

