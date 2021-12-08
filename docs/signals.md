Signals
=======

* `django_opensearch_dsl.signals.post_index`
  Sent after document indexing is completed. (not applicable for `parallel` indexing). Provides the following arguments:

    * `sender`
      A subclass of `django_opensearch_dsl.documents.Document` used to perform indexing.

    * `instance`
      A `django_opensearch_dsl.documents.Document` subclass instance.

    * `actions`
      A generator containing document data that were sent to opensearch for indexing.

    * `response`
      The response from `bulk()` function of `opensearch-py`, which includes `success` count and `failed` count
      or `error` list.
