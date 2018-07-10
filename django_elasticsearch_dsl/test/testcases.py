import re
from ..registries import registry


class ESTestCase(object):
    _index_suffixe = '_ded_test'

    @classmethod
    def setUpClass(cls):
        for doc in registry.get_documents():
            doc._doc_type.index += cls._index_suffixe

        for index in registry.get_indices():
            index._name += cls._index_suffixe
            index.delete(ignore=[404, 400])
            index.create()

        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        pattern = re.compile(cls._index_suffixe + '$')

        for doc in registry.get_documents():
            doc._doc_type.index = pattern.sub('', doc._doc_type.index)

        for index in registry.get_indices():
            index.delete(ignore=[404, 400])
            index._name = pattern.sub('', index._name)

        super().tearDownClass()
