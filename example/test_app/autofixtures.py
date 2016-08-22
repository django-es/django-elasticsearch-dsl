from datetime import datetime
from .models import Car, Manufacturer, Ad, COUNTRIES
from autofixture import generators, register, AutoFixture


class CarAutoFixture(AutoFixture):
    field_values = {
        'name': generators.StringGenerator(min_length=3, max_length=12),
        'launched': generators.DateTimeGenerator(
            min_date=datetime(1950, 1, 1),
            max_date=datetime(2015, 12, 31)
        ),
        'type': generators.ChoicesGenerator(
            values=('se', '4x', 'co', 'br')),
    }


class ManufacturerAutoFixture(AutoFixture):
    field_values = {
        'name': generators.StringGenerator(min_length=3, max_length=12),
        'created': generators.DateTimeGenerator(
            min_date=datetime(1900, 1, 1),
            max_date=datetime(2015, 12, 31)
        ),
        'country_code': generators.ChoicesGenerator(
            values=(COUNTRIES.keys())),
    }


class AdAutoFixture(AutoFixture):
    field_values = {
        'title': generators.LoremWordGenerator(),
        'description': generators.LoremHTMLGenerator(),
    }

register(Car, CarAutoFixture)
register(Manufacturer, ManufacturerAutoFixture)
register(Ad, AdAutoFixture)
