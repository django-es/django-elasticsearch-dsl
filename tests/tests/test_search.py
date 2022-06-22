from django.test import TestCase
from opensearch_dsl import Q

from django_dummy_app.commands import call_command
from django_dummy_app.documents import CountryDocument, ContinentDocument
from django_dummy_app.models import Country, Continent


class DocumentTestCase(TestCase):
    fixtures = ["tests/django_dummy_app/geography_data.json"]

    def setUp(self) -> None:
        call_command("opensearch", "index", "delete", force=True, ignore_error=True, verbosity=0)

    def test_search_country(self):
        call_command("opensearch", "index", "create", CountryDocument.Index.name, force=True, verbosity=0)

        CountryDocument().update(CountryDocument().get_indexing_queryset(), "index", refresh=True)
        self.assertEqual(
            set(CountryDocument.search().query("term", **{"continent.name": "Europe"}).extra(size=300).to_queryset()),
            set(Country.objects.filter(continent__name="Europe")),
        )

    def test_search_country_cache(self):
        call_command("opensearch", "index", "create", CountryDocument.Index.name, force=True, verbosity=0)

        CountryDocument().update(CountryDocument().get_indexing_queryset(), "index", refresh=True)
        search = CountryDocument.search().query("term", **{"continent.name": "Europe"}).extra(size=300)
        search.execute()
        self.assertEqual(
            set(search.to_queryset(keep_order=True)), set(Country.objects.filter(continent__name="Europe"))
        )

    def test_search_country_keep_order(self):
        call_command("opensearch", "index", "create", CountryDocument.Index.name, force=True, verbosity=0)

        CountryDocument().update(CountryDocument().get_indexing_queryset(), "index", refresh=True)
        search = CountryDocument.search().query("term", **{"continent.name": "Europe"}).extra(size=300)
        self.assertEqual(
            set(search.to_queryset(keep_order=True)), set(Country.objects.filter(continent__name="Europe"))
        )

    def test_search_country_refresh_default_to_document(self):
        call_command("opensearch", "index", "create", CountryDocument.Index.name, force=True, verbosity=0)

        CountryDocument().update(CountryDocument().get_indexing_queryset(), "index", refresh=True)
        self.assertEqual(
            set(CountryDocument.search().query("term", **{"continent.name": "Europe"}).extra(size=300).to_queryset()),
            set(Country.objects.filter(continent__name="Europe")),
        )

    def test_search_country_refresh_default_to_settings(self):
        call_command("opensearch", "index", "create", ContinentDocument.Index.name, force=True, verbosity=0)

        ContinentDocument().update(ContinentDocument().get_indexing_queryset(), "index", refresh=True)
        search = ContinentDocument.search().query(
            "nested", path="countries", query=Q("term", **{"countries.name": "France"})
        )
        self.assertEqual(set(search.to_queryset()), set(Continent.objects.filter(countries__name="France")))

    def test_update_instance(self):
        call_command("opensearch", "index", "create", ContinentDocument.Index.name, force=True, verbosity=0)
        ContinentDocument().update(Continent.objects.get(countries__name="France"), "index", refresh=True)
        search = ContinentDocument.search().query(
            "nested", path="countries", query=Q("term", **{"countries.name": "France"})
        )
        self.assertEqual(set(search.to_queryset()), set(Continent.objects.filter(countries__name="France")))
