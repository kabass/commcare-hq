from django.test import SimpleTestCase
from corehq.form_processor.utils import adjust_datetimes


class AdjustDatetimesTest(SimpleTestCase):

    def test_date_no_change(self):
        self.assertEqual(adjust_datetimes({'date': '2015-04-03'}),
                         {'date': '2015-04-03'})

    def test_no_tz(self):
        self.assertEqual(
            adjust_datetimes({'datetime': '2013-03-09T06:30:09.007'}),
            {'datetime': '2013-03-09T06:30:09.007000Z'}
        )

    def test_strip_tz(self):
        self.assertEqual(
            adjust_datetimes({'datetime': '2013-03-09T06:30:09.007+03'}),
            {'datetime': '2013-03-09T03:30:09.007000Z'}
        )

    def test_match_no_parse(self):
        fake_datetime = '2015-07-14 2015-06-07 '
        self.assertEqual(
            adjust_datetimes({'fake_datetime': fake_datetime}),
            {'fake_datetime': fake_datetime}
        )
