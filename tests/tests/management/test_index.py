import functools
import os

from django.test import SimpleTestCase

from django_dummy_app.commands import call_command
from django_dummy_app.documents import CountryDocument, ContinentDocument, EventDocument
from django_opensearch_dsl.registries import registry


class IndexTestCase(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        devnull = open(os.devnull, "w")
        cls.call_command = functools.partial(call_command, stdout=devnull, stderr=devnull)

    def setUp(self) -> None:
        indices = registry.get_indices()
        for i in indices:
            i.delete(ignore_unavailable=True)

    def test_index_creation_all(self):
        indices = registry.get_indices()

        self.assertFalse(any(map(lambda i: i.exists(), indices)))
        self.call_command("opensearch", "index", "create", force=True)
        self.assertTrue(all(map(lambda i: i.exists(), indices)))

    def test_index_creation_one(self):
        continent_document = ContinentDocument()
        country_document = CountryDocument()
        event_document = EventDocument()

        self.assertFalse(continent_document._index.exists())
        self.assertFalse(country_document._index.exists())
        self.assertFalse(event_document._index.exists())
        self.call_command("opensearch", "index", "create", country_document.Index.name, force=True)
        self.assertFalse(continent_document._index.exists())
        self.assertTrue(country_document._index.exists())
        self.assertFalse(event_document._index.exists())

    def test_index_creation_two(self):
        continent_document = ContinentDocument()
        country_document = CountryDocument()
        event_document = EventDocument()

        self.assertFalse(continent_document._index.exists())
        self.assertFalse(country_document._index.exists())
        self.assertFalse(event_document._index.exists())
        self.call_command(
            "opensearch",
            "index",
            "create",
            country_document.Index.name,
            event_document.Index.name,
            force=True,
        )
        self.assertFalse(continent_document._index.exists())
        self.assertTrue(country_document._index.exists())
        self.assertTrue(event_document._index.exists())

    def test_index_creation_error(self):
        country_document = CountryDocument()
        self.call_command("opensearch", "index", "create", country_document.Index.name, force=True)

        self.call_command("opensearch", "index", "create", country_document.Index.name, force=True, ignore_error=True)
        with self.assertRaises(SystemExit):
            self.call_command("opensearch", "index", "create", country_document.Index.name, force=True)

    def test_index_deletion_all(self):
        self.call_command("opensearch", "index", "create", force=True)
        indices = registry.get_indices()

        self.assertTrue(all(map(lambda i: i.exists(), indices)))
        self.call_command("opensearch", "index", "delete", force=True)
        self.assertFalse(any(map(lambda i: i.exists(), indices)))

    def test_index_deletion_one(self):
        self.call_command("opensearch", "index", "create", force=True)
        continent_document = ContinentDocument()
        country_document = CountryDocument()
        event_document = EventDocument()

        self.assertTrue(continent_document._index.exists())
        self.assertTrue(country_document._index.exists())
        self.assertTrue(event_document._index.exists())
        self.call_command("opensearch", "index", "delete", country_document.Index.name, force=True)
        self.assertTrue(continent_document._index.exists())
        self.assertFalse(country_document._index.exists())
        self.assertTrue(event_document._index.exists())

    def test_index_deletion_two(self):
        self.call_command("opensearch", "index", "create", force=True)
        continent_document = ContinentDocument()
        country_document = CountryDocument()
        event_document = EventDocument()

        self.assertTrue(continent_document._index.exists())
        self.assertTrue(country_document._index.exists())
        self.assertTrue(event_document._index.exists())
        self.call_command(
            "opensearch",
            "index",
            "delete",
            country_document.Index.name,
            event_document.Index.name,
            force=True,
        )
        self.assertTrue(continent_document._index.exists())
        self.assertFalse(country_document._index.exists())
        self.assertFalse(event_document._index.exists())

    def test_index_deletion_error(self):
        country_document = CountryDocument()

        self.call_command("opensearch", "index", "delete", country_document.Index.name, force=True, ignore_error=True)
        with self.assertRaises(SystemExit):
            self.call_command("opensearch", "index", "delete", country_document.Index.name, force=True)

    def test_index_rebuild_two(self):
        continent_document = ContinentDocument()
        country_document = CountryDocument()
        event_document = EventDocument()
        self.call_command(
            "opensearch",
            "index",
            "create",
            continent_document.Index.name,
            event_document.Index.name,
            force=True,
        )

        self.assertTrue(continent_document._index.exists())
        self.assertFalse(country_document._index.exists())
        self.assertTrue(event_document._index.exists())
        self.call_command(
            "opensearch",
            "index",
            "rebuild",
            country_document.Index.name,
            event_document.Index.name,
            force=True,
        )
        self.assertTrue(continent_document._index.exists())
        self.assertTrue(country_document._index.exists())
        self.assertTrue(event_document._index.exists())

    def test_unknown_index(self):
        with self.assertRaises(SystemExit):
            self.call_command("opensearch", "index", "create", "unknown")
