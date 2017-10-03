from mock import Mock

from django.db import models

from django_elasticsearch_dsl.documents import DocType


class WithFixturesMixin(object):

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

    def _generate_doc_mock(
        self, _model, index=None, mock_qs=None,
        _ignore_signals=False, _related_models=None
    ):
        class Doc(DocType):
            class Meta:
                model = _model
                ignore_signals = _ignore_signals
                related_models = _related_models if (
                    _related_models) is not None else []

        Doc.update = Mock()
        if mock_qs:
            Doc.get_queryset = Mock(return_value=mock_qs)
        if _related_models:
            Doc.get_instances_from_related = Mock()

        if index:
            self.registry.register(index, Doc)

        return Doc
