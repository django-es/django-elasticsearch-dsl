from datetime import datetime
from django.test import TestCase
from django_elasticsearch_dsl.test import ESTestCase
from .documents import CarDocument
from .models import Car, Manufacturer


class IntegrationTestCase(ESTestCase, TestCase):
    def setUp(self):
        super(IntegrationTestCase, self).setUp()
        manufacturer = Manufacturer(name="Peugeot",
                                    created=datetime(1920, 10, 9, 0, 0),
                                    country_code="FR")
        manufacturer.save()
        self.car1 = Car(name="508", launched=datetime(2010, 10, 9, 0, 0),
                        manufacturer=manufacturer)
        self.car1.save()
        self.car2 = Car(name="208", launched=datetime(2010, 10, 9, 0, 0),
                        manufacturer=manufacturer)
        self.car2.save()
        self.car3 = Car(name="308", launched=datetime(2010, 10, 9, 0, 0))
        self.car3.save()

    def test_get_indexed_cars_by_name(self):
        s = CarDocument.search().query("match", name=self.car2.name)
        result = s.execute()
        self.assertEqual(len(result), 1)
        car2_item = result[0]
        self.assertEqual(car2_item.ads, [])
        self.assertEqual(car2_item.name, self.car2.name)
        self.assertEqual(car2_item.launched, self.car2.launched)
        self.assertEqual(car2_item.manufacturer.name,
                         self.car2.manufacturer.name)
        self.assertEqual(car2_item.manufacturer.country, "France")

        s = CarDocument.search().query("match", name=self.car3.name)
        result = s.execute()
        car3_item = result[0]
        self.assertEqual(car3_item.manufacturer, None)
        self.assertEqual(car3_item.name, self.car3.name)
