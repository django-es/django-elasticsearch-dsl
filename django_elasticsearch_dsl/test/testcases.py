import re
from ..registries import registry


class ESTestCase(object):
    def setUp(self):
        for index in registry.get_indices():
            index._name += "_ded_test"
            index.delete(ignore=[404, 400])
            index.create()

        super(ESTestCase, self).setUp()

    def tearDown(self):
        for index in registry.get_indices():
            index.delete(ignore=[404, 400])
            index._name = re.sub("_ded_test$", "",
                                 index._name)

        super(ESTestCase, self).tearDown()
