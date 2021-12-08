import datetime

from django.test import TestCase

from django_opensearch_dsl.management import types


class TypeTestCase(TestCase):
    """Test parsers defined in `dgeg.types`."""

    def test_none_parser(self):
        self.assertEqual(None, types.none_parser(""))
        self.assertEqual(..., types.none_parser("1"))
        self.assertEqual(..., types.none_parser("0"))
        self.assertEqual(..., types.none_parser("string"))

    def test_float_parser(self):
        self.assertEqual(0.0, types.float_parser("0"))
        self.assertEqual(0.1, types.float_parser("0.1"))
        self.assertEqual(..., types.float_parser(""))
        self.assertEqual(..., types.float_parser("string"))

    def test_int_parser(self):
        self.assertEqual(0, types.int_parser("0"))
        self.assertEqual(1, types.int_parser("1"))
        self.assertEqual(..., types.int_parser("0.0"))
        self.assertEqual(..., types.int_parser("0.1"))
        self.assertEqual(..., types.int_parser(""))
        self.assertEqual(..., types.int_parser("string"))

    def test_datetime_parser(self):
        self.assertEqual(
            datetime.datetime(2020, 8, 20, 0, 0, tzinfo=datetime.timezone.utc), types.datetime_parser("2020-08-20")
        )
        self.assertEqual(
            datetime.datetime(2020, 8, 1, 0, 0, tzinfo=datetime.timezone.utc), types.datetime_parser("2020-08")
        )
        self.assertEqual(
            datetime.datetime(2020, 1, 1, 0, 0, tzinfo=datetime.timezone.utc), types.datetime_parser("2020")
        )
        self.assertEqual(
            datetime.datetime(2020, 8, 20, 14, 20, 47, tzinfo=datetime.timezone(datetime.timedelta(0), '+0000')),
            types.datetime_parser("2020-08-20T14:20:47+00:00")
        )
        self.assertEqual(
            datetime.datetime(2020, 8, 20, 14, 20, 47, tzinfo=datetime.timezone.utc),
            types.datetime_parser("2020-08-20T14:20:47Z")
        )
        self.assertEqual(
            datetime.datetime(2020, 8, 20, 14, 20, 47, tzinfo=datetime.timezone.utc),
            types.datetime_parser("20200820T142047")
        )
        self.assertEqual(
            datetime.datetime(2020, 8, 17, 0, 0, tzinfo=datetime.timezone.utc),
            types.datetime_parser("2020-W34")
        )
        self.assertEqual(
            datetime.datetime(2020, 8, 20, 0, 0, tzinfo=datetime.timezone.utc), types.datetime_parser("2020-W34-4")
        )
        self.assertEqual(
            datetime.datetime(2020, 8, 20, 0, 0, tzinfo=datetime.timezone.utc), types.datetime_parser("2020-233")
        )
        self.assertEqual(..., types.datetime_parser("0"))
        self.assertEqual(..., types.datetime_parser("0.0"))
        self.assertEqual(..., types.datetime_parser(""))
        self.assertEqual(..., types.datetime_parser("string"))

    def test_list_parser(self):
        self.assertEqual([1, 2, 3], types.list_parser("1,2,3"))
        self.assertEqual([1.1, 2.2, 3.3], types.list_parser("1.1,2.2,3.3"))
        self.assertEqual(["abc", "def"], types.list_parser("abc,def"))
        self.assertEqual(
            [
                datetime.datetime(2020, 8, 20, 0, 0, tzinfo=datetime.timezone.utc),
                datetime.datetime(2020, 8, 21, 0, 0, tzinfo=datetime.timezone.utc),
            ],
            types.list_parser("2020-08-20,2020-08-21")
        )

    def test_parsers(self):
        self.assertEqual(None, types.parse(""))
        self.assertEqual(0.1, types.parse("0.1"))
        self.assertEqual(1, types.parse("1"))
        self.assertEqual(
            datetime.datetime(2020, 8, 20, 0, 0, tzinfo=datetime.timezone.utc), types.parse("2020-08-20")
        )
        self.assertEqual([1, 2, 3], types.parse("1,2,3"))
