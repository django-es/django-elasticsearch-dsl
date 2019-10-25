import re
from ..registries import registry


class ESTestCase(object):
    _index_suffixe = '_ded_test'

    def setUp(self):
        for doc in registry.get_documents():
            doc._index._name += self._index_suffixe

        for index in registry.get_indices():
            index._name += self._index_suffixe
            index.delete(ignore=[404, 400])
            index.create()

        super(ESTestCase, self).setUp()

    def tearDown(self):
        pattern = re.compile(self._index_suffixe + '$')

        for index in registry.get_indices():
            index.delete(ignore=[404, 400])
            index._name = pattern.sub('', index._name)

        for doc in registry.get_documents():
            doc._index._name = pattern.sub('', doc._index._name)

        super(ESTestCase, self).tearDown()
