import functools
import os
import time

from django.test import TestCase

from django_dummy_app.commands import call_command
from django_dummy_app.documents import CountryDocument, ContinentDocument, EventDocument
from django_dummy_app.models import Country, Event, Continent
from django_opensearch_dsl.registries import registry


class DocumentTestCase(TestCase):
    fixtures = ["tests/django_dummy_app/geography_data.json"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        devnull = open(os.devnull, "w")
        cls.call_command = functools.partial(call_command, stdout=devnull, stderr=devnull)

    def setUp(self) -> None:
        indices = registry.get_indices()
        for i in indices:
            i.delete(ignore_unavailable=True)

    def test_unknown_index(self):
        with self.assertRaises(SystemExit):
            self.call_command("opensearch", "document", "index", "-iunknown")

    def test_index_not_created(self):
        with self.assertRaises(SystemExit):
            self.call_command("opensearch", "document", "index", f"-i{CountryDocument.Index.name}")

    def test_unknown_field(self):
        self.call_command("opensearch", "index", "create", CountryDocument.Index.name, force=True)
        with self.assertRaises(SystemExit):
            self.call_command(
                "opensearch",
                "document",
                "index",
                f"-i{CountryDocument.Index.name}",
                force=True,
                filters=[("unknown_field", "value")],
                refresh=True,
            )

    def test_index_all(self):
        self.call_command("opensearch", "index", "create", force=True)

        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        self.call_command("opensearch", "document", "index", force=True, refresh=True)
        self.assertEqual(CountryDocument.search().count(), Country.objects.count())
        self.assertEqual(ContinentDocument.search().count(), Continent.objects.count())
        self.assertEqual(EventDocument.search().count(), Event.objects.exclude(country__name="France").count())

    def test_index_all_parallel(self):
        self.call_command("opensearch", "index", "create", force=True)

        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        self.call_command("opensearch", "document", "index", force=True, refresh=True)
        self.assertEqual(CountryDocument.search().count(), Country.objects.count())
        self.assertEqual(ContinentDocument.search().count(), Continent.objects.count())
        self.assertEqual(EventDocument.search().count(), Event.objects.exclude(country__name="France").count())

    def test_index_one(self):
        self.call_command("opensearch", "index", "create", force=True)

        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        self.call_command(
            "opensearch", "document", "index", f"-i{CountryDocument.Index.name}", force=True, refresh=True
        )
        self.assertEqual(CountryDocument.search().count(), Country.objects.count())
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)

    def test_index_filters_equal(self):
        self.call_command("opensearch", "index", "create", force=True)

        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        self.call_command(
            "opensearch",
            "document",
            "index",
            f"-i{CountryDocument.Index.name}",
            force=True,
            filters=[("continent__name", "Europe")],
            refresh=True,
        )
        self.assertEqual(
            CountryDocument.search().count(),
            Country.objects.select_related("continent").filter(continent__name="Europe").count(),
        )
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)

    def test_index_filters_gte(self):
        self.call_command("opensearch", "index", "create", force=True)

        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        self.call_command(
            "opensearch",
            "document",
            "index",
            f"-i{CountryDocument.Index.name}",
            force=True,
            filters=[("population__gte", 1000000)],
            refresh=True,
        )
        self.assertEqual(
            CountryDocument.search().count(),
            Country.objects.select_related("continent").filter(population__gte=1000000).count(),
        )
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)

    def test_index_excludes_gte(self):
        self.call_command("opensearch", "index", "create", force=True)

        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        self.call_command(
            "opensearch",
            "document",
            "index",
            f"-i{CountryDocument.Index.name}",
            force=True,
            excludes=[("population__gte", 1000000)],
            refresh=True,
        )
        self.assertEqual(
            CountryDocument.search().count(),
            Country.objects.select_related("continent").exclude(population__gte=1000000).count(),
        )
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)

    def test_index_filters_gte_lte(self):
        self.call_command("opensearch", "index", "create", force=True)

        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        self.call_command(
            "opensearch",
            "document",
            "index",
            f"-i{CountryDocument.Index.name}",
            force=True,
            filters=[("population__gte", 1000000), ("population__lte", 10000000)],
            refresh=True,
        )
        self.assertEqual(
            CountryDocument.search().count(),
            Country.objects.select_related("continent")
            .filter(population__gte=1000000, population__lte=10000000)
            .count(),
        )
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)

    def test_index_excludes_gte_lte(self):
        self.call_command("opensearch", "index", "create", force=True)

        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        self.call_command(
            "opensearch",
            "document",
            "index",
            f"-i{CountryDocument.Index.name}",
            force=True,
            excludes=[("population__gte", 1000000), ("population__lte", 10000000)],
            refresh=True,
        )
        self.assertEqual(
            CountryDocument.search().count(),
            Country.objects.select_related("continent")
            .exclude(population__gte=1000000, population__lte=10000000)
            .count(),
        )
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)

    def test_index_count(self):
        self.call_command("opensearch", "index", "create", force=True)

        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        self.call_command("opensearch", "document", "index", force=True, count=3, refresh=True)
        self.assertEqual(ContinentDocument.search().count(), 3)
        self.assertEqual(CountryDocument.search().count(), 3)
        self.assertEqual(EventDocument.search().count(), 3)

    def test_index_missing(self):
        self.call_command("opensearch", "index", "create", force=True)

        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        self.call_command("opensearch", "document", "index", force=True, count=3, refresh=True)
        self.assertEqual(ContinentDocument.search().count(), 3)
        self.assertEqual(CountryDocument.search().count(), 3)
        self.assertEqual(EventDocument.search().count(), 3)
        self.call_command("opensearch", "document", "index", force=True, missing=True, refresh=True)
        self.assertEqual(CountryDocument.search().count(), Country.objects.count())
        self.assertEqual(ContinentDocument.search().count(), Continent.objects.count())
        self.assertEqual(EventDocument.search().count(), Event.objects.exclude(country__name="France").count())

    def test_index_not_refresh(self):
        self.call_command("opensearch", "index", "create", force=True)

        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        self.call_command("opensearch", "document", "index", force=True, count=3)
        self.assertEqual(ContinentDocument.search().count(), 0)
        self.assertEqual(CountryDocument.search().count(), 0)
        self.assertEqual(EventDocument.search().count(), 0)
        time.sleep(1)
        self.assertEqual(ContinentDocument.search().count(), 3)
        self.assertEqual(CountryDocument.search().count(), 3)
        self.assertEqual(EventDocument.search().count(), 3)
