from django.test import SimpleTestCase

from routing.risk import Risk, assess, rain_risk, snow_risk, wind_risk


class WindTests(SimpleTestCase):
    def test_bands_for_light_load(self):
        cases = [(0, Risk.LOW), (24.9, Risk.LOW), (25, Risk.MODERATE), (34.9, Risk.MODERATE), (35, Risk.HIGH),
                 (44.9, Risk.HIGH), (45, Risk.SEVERE), (54.9, Risk.SEVERE), (55, Risk.NO_TRAVEL), (70, Risk.NO_TRAVEL)]
        for mph, expected in cases:
            with self.subTest(mph=mph):
                self.assertEqual(wind_risk(mph, 10_000), expected)

    def test_55_mph_is_no_travel_for_any_load(self):
        self.assertEqual(wind_risk(55, 0), Risk.NO_TRAVEL)

    def test_45_to_54_with_more_than_30k_is_no_travel(self):
        self.assertEqual(wind_risk(45, 30_001), Risk.NO_TRAVEL)
        self.assertEqual(wind_risk(54, 45_000), Risk.NO_TRAVEL)
        self.assertEqual(wind_risk(50, 30_000), Risk.SEVERE)  # exactly 30k is not "more than"

    def test_35_to_44_with_more_than_40k_is_severe(self):
        self.assertEqual(wind_risk(35, 40_001), Risk.SEVERE)
        self.assertEqual(wind_risk(44, 80_000), Risk.SEVERE)
        self.assertEqual(wind_risk(40, 40_000), Risk.HIGH)

    def test_load_does_not_change_calm_wind(self):
        self.assertEqual(wind_risk(20, 80_000), Risk.LOW)
        self.assertEqual(wind_risk(30, 80_000), Risk.MODERATE)


class PrecipitationTests(SimpleTestCase):
    def test_rain_bands(self):
        cases = [(0.0, Risk.LOW), (0.09, Risk.LOW), (0.10, Risk.MODERATE), (0.25, Risk.HIGH), (0.49, Risk.HIGH),
                 (0.50, Risk.SEVERE), (1.00, Risk.SEVERE), (1.01, Risk.NO_TRAVEL)]
        for value, expected in cases:
            with self.subTest(rain=value):
                self.assertEqual(rain_risk(value), expected)

    def test_snow_bands(self):
        cases = [(0.4, Risk.LOW), (0.5, Risk.MODERATE), (1.0, Risk.HIGH), (2.0, Risk.SEVERE), (3.0, Risk.SEVERE),
                 (3.1, Risk.NO_TRAVEL)]
        for value, expected in cases:
            with self.subTest(snow=value):
                self.assertEqual(snow_risk(value), expected)


class AssessTests(SimpleTestCase):
    def test_worst_condition_wins(self):
        a = assess(wind_mph=10, rain_in_hr=0.3, snow_in_hr=0.6, load_lb=5_000)
        self.assertEqual(a.level, Risk.HIGH)
        self.assertEqual(a.reasons, ["rain 0.30 in/hr"])

    def test_reason_mentions_the_load_when_it_raised_the_level(self):
        a = assess(wind_mph=48, rain_in_hr=0, snow_in_hr=0, load_lb=36_000)
        self.assertEqual(a.level, Risk.NO_TRAVEL)
        self.assertIn("36,000 lb", a.reasons[0])

    def test_calm_weather_has_no_reasons(self):
        self.assertEqual(assess(5, 0, 0, 40_000).reasons, [])
