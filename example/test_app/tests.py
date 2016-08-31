from datetime import datetime
from django.test import TestCase
from django_elasticsearch_dsl.test import ESTestCase
from .documents import CarDocument
from .models import Car, Manufacturer, COUNTRIES


class IntegrationTestCase(ESTestCase, TestCase):
    def setUp(self):
        super(IntegrationTestCase, self).setUp()
        self.manufacturer = Manufacturer(name="Peugeot",
                                         created=datetime(1920, 10, 9, 0, 0),
                                         country_code="FR")
        self.manufacturer.save()
        self.car1 = Car(name="508", launched=datetime(2010, 10, 9, 0, 0),
                        manufacturer=self.manufacturer)
        self.car1.save()
        self.car2 = Car(name="208", launched=datetime(2010, 10, 9, 0, 0),
                        manufacturer=self.manufacturer)
        self.car2.save()
        self.car3 = Car(name="308", launched=datetime(2010, 10, 9, 0, 0))
        self.car3.save()

    def test_get_car_doc(self):
        s = CarDocument.search().query("match", name=self.car2.name)
        result = s.execute()
        self.assertEqual(len(result), 1)
        car2_doc = result[0]
        self.assertEqual(car2_doc.ads, [])
        self.assertEqual(car2_doc.name, self.car2.name)
        self.assertEqual(int(car2_doc.meta.id), self.car2.pk)
        self.assertEqual(car2_doc.launched, self.car2.launched)
        self.assertEqual(car2_doc.manufacturer.name,
                         self.car2.manufacturer.name)
        self.assertEqual(car2_doc.manufacturer.country,
                         COUNTRIES[self.manufacturer.country_code])

        s = CarDocument.search().query("match", name=self.car3.name)
        result = s.execute()
        car3_doc = result[0]
        self.assertEqual(car3_doc.manufacturer, {})
        self.assertEqual(car3_doc.name, self.car3.name)
        self.assertEqual(int(car3_doc.meta.id), self.car3.pk)

    def test_doc_to_dict(self):
        s = CarDocument.search().query("match", name=self.car2.name)
        result = s.execute()
        self.assertEqual(len(result), 1)
        car2_doc = result[0]
        self.assertEqual(car2_doc.to_dict(), {
            'type': self.car2.type,
            'launched': self.car2.launched,
            'name': self.car2.name,
            'manufacturer': {
                'name': self.manufacturer.name,
                'country': COUNTRIES[self.manufacturer.country_code],
            }
        })

        s = CarDocument.search().query("match", name=self.car3.name)
        result = s.execute()
        self.assertEqual(len(result), 1)
        car3_doc = result[0]
        self.assertEqual(car3_doc.to_dict(), {
            'type': self.car3.type,
            'launched': self.car3.launched,
            'name': self.car3.name,
        })
