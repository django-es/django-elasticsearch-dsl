from django.test import SimpleTestCase

from django_dummy_app.commands import call_command
from django_dummy_app.documents import CountryDocument, ContinentDocument, EventDocument
from django_opensearch_dsl.registries import registry


class IndexTestCase(SimpleTestCase):

    def setUp(self) -> None:
        call_command("opensearch", "index", "delete", force=True, ignore_error=True, verbosity=0)

    def test_index_creation_all(self):
        indices = registry.get_indices()

        self.assertFalse(any(map(lambda i: i.exists(), indices)))
        call_command("opensearch", "index", "create", force=True, verbosity=0)
        self.assertTrue(all(map(lambda i: i.exists(), indices)))

    def test_index_creation_one(self):
        continent_document = ContinentDocument()
        country_document = CountryDocument()
        event_document = EventDocument()

        self.assertFalse(continent_document._index.exists())
        self.assertFalse(country_document._index.exists())
        self.assertFalse(event_document._index.exists())
        call_command(
            "opensearch", "index", "create", country_document.Index.name, force=True, verbosity=0
        )
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
        call_command(
            "opensearch", "index", "create", country_document.Index.name, event_document.Index.name,
            force=True, verbosity=0
        )
        self.assertFalse(continent_document._index.exists())
        self.assertTrue(country_document._index.exists())
        self.assertTrue(event_document._index.exists())

    def test_index_creation_error(self):
        country_document = CountryDocument()
        call_command("opensearch", "index", "create", country_document.Index.name, force=True, verbosity=0)

        call_command(
            "opensearch", "index", "create", country_document.Index.name, force=True, verbosity=0, ignore_error=True
        )
        with self.assertRaises(SystemExit):
            call_command("opensearch", "index", "create", country_document.Index.name, force=True, verbosity=0)

    def test_index_deletion_all(self):
        call_command("opensearch", "index", "create", force=True, verbosity=0)
        indices = registry.get_indices()

        self.assertTrue(all(map(lambda i: i.exists(), indices)))
        call_command("opensearch", "index", "delete", force=True, verbosity=0)
        self.assertFalse(any(map(lambda i: i.exists(), indices)))

    def test_index_deletion_one(self):
        call_command("opensearch", "index", "create", force=True, verbosity=0)
        continent_document = ContinentDocument()
        country_document = CountryDocument()
        event_document = EventDocument()

        self.assertTrue(continent_document._index.exists())
        self.assertTrue(country_document._index.exists())
        self.assertTrue(event_document._index.exists())
        call_command(
            "opensearch", "index", "delete", country_document.Index.name, force=True, verbosity=0
        )
        self.assertTrue(continent_document._index.exists())
        self.assertFalse(country_document._index.exists())
        self.assertTrue(event_document._index.exists())

    def test_index_deletion_two(self):
        call_command("opensearch", "index", "create", force=True, verbosity=0)
        continent_document = ContinentDocument()
        country_document = CountryDocument()
        event_document = EventDocument()

        self.assertTrue(continent_document._index.exists())
        self.assertTrue(country_document._index.exists())
        self.assertTrue(event_document._index.exists())
        call_command(
            "opensearch", "index", "delete", country_document.Index.name, event_document.Index.name,
            force=True, verbosity=0
        )
        self.assertTrue(continent_document._index.exists())
        self.assertFalse(country_document._index.exists())
        self.assertFalse(event_document._index.exists())

    def test_index_deletion_error(self):
        country_document = CountryDocument()

        call_command(
            "opensearch", "index", "delete", country_document.Index.name, force=True, verbosity=0, ignore_error=True
        )
        with self.assertRaises(SystemExit):
            call_command("opensearch", "index", "delete", country_document.Index.name, force=True, verbosity=0)

    def test_index_rebuild_two(self):
        continent_document = ContinentDocument()
        country_document = CountryDocument()
        event_document = EventDocument()
        call_command(
            "opensearch", "index", "create", continent_document.Index.name, event_document.Index.name, force=True,
            verbosity=0
        )

        self.assertTrue(continent_document._index.exists())
        self.assertFalse(country_document._index.exists())
        self.assertTrue(event_document._index.exists())
        call_command(
            "opensearch", "index", "rebuild", country_document.Index.name, event_document.Index.name, force=True,
            verbosity=0
        )
        self.assertTrue(continent_document._index.exists())
        self.assertTrue(country_document._index.exists())
        self.assertTrue(event_document._index.exists())

    def test_unknown_index(self):
        with self.assertRaises(SystemExit):
            call_command("opensearch", "index", "create", "unknown", verbosity=0)
