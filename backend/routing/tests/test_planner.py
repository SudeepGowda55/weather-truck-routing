from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from routing.geo import cumulative_miles, decode_polyline, haversine_mi, overlap_share
from routing.planner import explain, make_checkpoints, rank_key, summarize
from routing.providers.valhalla import Route

DEPART = datetime(2026, 1, 5, 6, 0, tzinfo=timezone.utc)


def straight_route(miles=120, mph=60):
    # a line going due north, roughly one point per mile
    points = [(35 + i / 69.0, -100.0) for i in range(miles + 1)]
    dist = cumulative_miles(points)
    secs = [d / mph * 3600 for d in dist]
    return Route(points, dist, secs, dist[-1], secs[-1], "fastest")


def route_json(name, no_travel=0, severe=0, high=0, avg=0.0, hours=10):
    return {"name": name, "duration_s": hours * 3600,
            "summary": {"miles_by_risk": {"no_travel": no_travel, "severe": severe, "high": high}, "average_risk": avg}}


class CheckpointTests(SimpleTestCase):
    def test_spacing_and_end_point(self):
        stops = make_checkpoints(straight_route(120), DEPART, 25)
        self.assertEqual([round(c.mile) for c in stops], [0, 25, 50, 75, 100, 120])

    def test_miles_add_up_to_the_route(self):
        route = straight_route(137)
        for every in (10, 25, 50):
            stops = make_checkpoints(route, DEPART, every)
            self.assertAlmostEqual(sum(c.covers_mi for c in stops), route.miles[-1], places=6)

    def test_eta_follows_route_time(self):
        stops = make_checkpoints(straight_route(120, mph=60), DEPART, 50)
        self.assertAlmostEqual((stops[1].eta - DEPART).total_seconds(), 50 * 60, delta=5)

    def test_short_tail_is_merged_into_the_last_checkpoint(self):
        stops = make_checkpoints(straight_route(100), DEPART, 50)
        self.assertEqual(len(stops), 3)


class SummaryTests(SimpleTestCase):
    def test_distance_weighted_average(self):
        readings = [{"risk": "low", "covers_mi": 30}, {"risk": "severe", "covers_mi": 10}]
        s = summarize(readings)
        self.assertEqual(s["miles_by_risk"]["severe"], 10)
        self.assertAlmostEqual(s["average_risk"], 0.75)
        self.assertEqual(s["worst"], "severe")


class RankingTests(SimpleTestCase):
    def test_order_follows_the_brief(self):
        routes = [
            route_json("fast but stormy", severe=20, hours=8),
            route_json("long and calm", hours=12),
            route_json("calm, some high", high=30, hours=9),
        ]
        ranked = sorted(routes, key=rank_key)
        self.assertEqual([r["name"] for r in ranked], ["long and calm", "calm, some high", "fast but stormy"])

    def test_time_breaks_ties(self):
        ranked = sorted([route_json("slow", hours=11), route_json("quick", hours=9)], key=rank_key)
        self.assertEqual(ranked[0]["name"], "quick")

    def test_no_travel_is_never_preferred(self):
        ranked = sorted([route_json("blocked", no_travel=5, hours=5), route_json("severe", severe=90, hours=15)], key=rank_key)
        self.assertEqual(ranked[0]["name"], "severe")

    def test_explanation_names_the_deciding_rule(self):
        best = route_json("Route B")
        text = explain(best, [route_json("Route A", severe=20), route_json("Route C", hours=11)])
        self.assertIn("Route A has 20 Severe miles vs 0", text)
        self.assertIn("Route C is 1 h 00 min slower", text)


class GeoTests(SimpleTestCase):
    def test_decode_polyline6(self):
        # "_izlhA~rlgdF_{geC~ywl@" is (38.5, -120.2), (40.7, -120.95) at precision 6
        self.assertEqual(decode_polyline("_izlhA~rlgdF_{geC~ywl@"), [(38.5, -120.2), (40.7, -120.95)])

    def test_haversine(self):
        self.assertAlmostEqual(haversine_mi((41.8781, -87.6298), (39.7392, -104.9903)), 920, delta=5)

    def test_overlap(self):
        a = straight_route(100).points
        shifted = [(lat, lon + 0.5) for lat, lon in a]  # ~26 miles east
        self.assertGreater(overlap_share(a, a), 0.99)
        self.assertLess(overlap_share(shifted, a), 0.01)


class ExpectedDeparture(SimpleTestCase):
    def test_eta_crosses_midnight(self):
        stops = make_checkpoints(straight_route(600, mph=60), DEPART + timedelta(hours=17), 100)
        self.assertEqual(stops[-1].eta.day, DEPART.day + 1)
