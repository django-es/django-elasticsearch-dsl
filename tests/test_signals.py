from mock import patch
from unittest import TestCase

from django.conf import settings

from elasticsearch.exceptions import ElasticsearchException

from django_elasticsearch_dsl import signals


class LogErrorsTestCase(TestCase):
    def test_log_errors_default(self):
        # Ensure default behavior is correct.
        self.assertFalse(signals.LOG_ERRORS)

    @patch('django_elasticsearch_dsl.signals.LOGGER')
    @patch('django_elasticsearch_dsl.signals.registry')
    def test_log_errors_on(self, m_registry, m_logger):
        # Object under test.
        rtsp = signals.RealTimeSignalProcessor(None)

        # Testing with the option enabled (non-default).
        signals.LOG_ERRORS = True
        try:
            # delete() is special. It logs all errors.
            m_registry.delete.side_effect = ElasticsearchException()
            rtsp.handle_delete(None, None)
            self.assertEqual(1, m_logger.exception.call_count)

            m_registry.delete.side_effect = ValueError()
            rtsp.handle_delete(None, None)
            self.assertEqual(2, m_logger.exception.call_count)

            # Other methods only log Elasticsearch specific errors and raise
            # # others.
            m_registry.delete_related.side_effect = ElasticsearchException()
            rtsp.handle_pre_delete(None, None)
            self.assertEqual(3, m_logger.exception.call_count)

            m_registry.delete_related.side_effect = ValueError()
            with self.assertRaises(ValueError):
               rtsp.handle_pre_delete(None, None)

            m_registry.update.side_effect = ElasticsearchException()
            rtsp.handle_save(None, None)
            self.assertEqual(4, m_logger.exception.call_count)

            m_registry.update.side_effect = ValueError()
            with self.assertRaises(ValueError):
               rtsp.handle_save(None, None)

        finally:
            signals.LOG_ERRORS = False

    @patch('django_elasticsearch_dsl.signals.LOGGER')
    @patch('django_elasticsearch_dsl.signals.registry')
    def test_log_errors_off(self, m_registry, m_logger):
        # Object under test.
        rtsp = signals.RealTimeSignalProcessor(None)
        
        # Default case, but be sure.
        signals.LOG_ERRORS = False

        # delete() is special. It ignores all errors, the LOG_ERRORS option
        # controls logging only.
        m_registry.delete.side_effect = ElasticsearchException
        rtsp.handle_delete(None, None)
        self.assertFalse(m_logger.exception.called)

        m_registry.delete.side_effect = ValueError()
        rtsp.handle_delete(None, None)
        self.assertFalse(m_logger.exception.called)

        # All other methods raise exceptions when LOG_ERRORS is disabled.
        m_registry.delete_related.side_effect = ElasticsearchException()
        with self.assertRaises(ElasticsearchException):
            rtsp.handle_pre_delete(None, None)
        self.assertFalse(m_logger.exception.called)

        m_registry.delete_related.side_effect = ValueError()
        with self.assertRaises(ValueError):
            rtsp.handle_pre_delete(None, None)
        self.assertFalse(m_logger.exception.called)

        m_registry.update.side_effect = ElasticsearchException()
        with self.assertRaises(ElasticsearchException):
            rtsp.handle_save(None, None)
        self.assertFalse(m_logger.exception.called)

        m_registry.update.side_effect = ValueError()
        with self.assertRaises(ValueError):
            rtsp.handle_save(None, None)
        self.assertFalse(m_logger.exception.called)
