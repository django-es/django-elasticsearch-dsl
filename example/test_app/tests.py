from datetime import datetime
from django.test import TestCase
from django_elasticsearch_dsl.test import ESTestCase
from .documents import CarDocument
from .models import Car, Manufacturer


class IntegrationTestCase(ESTestCase, TestCase):
    def test_car_indexed(self):
        manufacturer = Manufacturer(name="Peugeot",
                                    created=datetime(1920, 10, 9, 0, 0),
                                    country_code="FR")
        manufacturer.save()
        car1 = Car(name="508", launched=datetime(2010, 10, 9, 0, 0),
                   manufacturer=manufacturer)
        car1.save()
        car2 = Car(name="208", launched=datetime(2010, 10, 9, 0, 0),
                   manufacturer=manufacturer)
        car2.save()
        car3 = Car(name="308", launched=datetime(2010, 10, 9, 0, 0),
                   manufacturer=manufacturer)
        car3.save()

        s = CarDocument.search().query("match", name="208")
        result = s.execute()
        self.assertEqual(len(result), 1)
        car2_item = result[0]
        self.assertEqual(car2_item.ads, [])
        self.assertEqual(car2_item.name, car2.name)
        self.assertEqual(car2_item.launched, car2.launched)
        self.assertEqual(car2_item.manufacturer.name, car2.manufacturer.name)
        self.assertEqual(car2_item.manufacturer.country, "France")
