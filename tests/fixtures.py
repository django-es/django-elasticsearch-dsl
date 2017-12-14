from mock import Mock

from django.db import models

from django_elasticsearch_dsl import Index
from django_elasticsearch_dsl.documents import DocType
from django_elasticsearch_dsl.registries import DocumentRegistry


class ModelA(models.Model):
    class Meta:
        app_label = 'foo'


class ModelB(models.Model):
    class Meta:
        app_label = 'foo'


class ModelC(models.Model):
    class Meta:
        app_label = 'bar'


class ModelD(models.Model):
    pass


class ModelE(models.Model):
    pass


class DocA1(DocType):
    get_queryset = Mock(return_value=Mock())
    update = Mock()
    get_instances_from_related = Mock()

    class Meta:
        model = ModelA


class DocA2(DocType):
    get_queryset = Mock(return_value=Mock())
    update = Mock()
    get_instances_from_related = Mock()

    class Meta:
        model = ModelA


class DocB1(DocType):
    get_queryset = Mock(return_value=Mock())
    update = Mock()
    get_instances_from_related = Mock()

    class Meta:
        model = ModelB


class DocC1(DocType):
    get_queryset = Mock(return_value=Mock())
    update = Mock()
    get_instances_from_related = Mock()

    class Meta:
        model = ModelC
        ignore_signals = True


class DocD1(DocType):
    get_queryset = Mock(return_value=Mock())
    update = Mock()
    get_instances_from_related = Mock(return_value=ModelD())

    class Meta:
        model = ModelD
        related_models = [ModelE]


class WithFixturesMixin(object):

    def setUp(self):
        self.registry = DocumentRegistry()
        self.index_1 = Index('index_1')
        self.index_2 = Index('index_2')
