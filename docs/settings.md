Settings
========

## `OPENSEARCH_DSL`

**Required**

`OPENSEARCH_DSL` is used to configure the connections to opensearch. It must at least define a `'default'` connection
with a given `'hosts'`:

```python
OPENSEARCH_DSL = {
    'default': {
        'hosts': 'localhost:9200'
    }
}
```

`OPENSEARCH_DSL` is passed
to [`opensearch_dsl_py.connections.configure()`](http://elasticsearch-dsl.readthedocs.io/en/stable/configuration.html#multiple-clusters)
.

## `OPENSEARCH_DSL_INDEX_SETTINGS`

Default: `{}`

Additional options passed to the `opensearch-dsl` Index settings (like `number_of_replicas` or `number_of_shards`).
See [Opensearch's index settings](https://opensearch.org/docs/latest/opensearch/rest-api/index-apis/create-index/#index-settings)
for more information.

## `OPENSEARCH_DSL_AUTO_REFRESH`

Default: `False`

Set to `True` to force
an [index refresh](https://www.elastic.co/guide/en/elasticsearch/reference/current/indices-refresh.html>) with update.

## `OPENSEARCH_DSL_PARALLEL`

Default: `False`

Run indexing in parallel using OpenSearch's parallel_bulk() method. Note that some databases (e.g. SQLite)
do not play well with this option.

## `OPENSEARCH_DSL_QUERYSET_PAGINATION`

Default: `4096`

Size of the chunk used when indexing data. Can be overriden by setting `queryset_pagination` inside `Document`'
s [`Django` subclass](document.md#document-id).

