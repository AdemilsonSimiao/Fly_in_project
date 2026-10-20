import os
import tempfile
import unittest

from graph import Graph
from parser import parse_map
from path_finding import Scheduler
from timeline import Timeline


class TimelineTestCase(unittest.TestCase):
    text = (
        "nb_drones: 2\n"
        "start_hub: s 0 0\n"
        "end_hub: g 2 0\n"
        "hub: r 1 0 [zone=restricted max_drones=2]\n"
        "connection: s-r [max_link_capacity=2]\n"
        "connection: r-g [max_link_capacity=2]\n"
    )

    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = os.path.join(directory.name, "map.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write(self.text)
        data = parse_map(path)
        self.graph = Graph(data)
        schedule = Scheduler(self.graph).plan(data.nb_drones)
        self.timeline = Timeline(self.graph, data.nb_drones, schedule)


class TestTimeline(TimelineTestCase):
    def test_first_frame_has_every_drone_at_the_start(self) -> None:
        first = self.timeline.places[0]
        self.assertEqual(sorted(first), [1, 2])
        for place in first.values():
            self.assertIs(place.zone, self.graph.start)
            self.assertIsNone(place.connection)

    def test_there_is_one_frame_per_turn_plus_the_first(self) -> None:
        self.assertEqual(len(self.timeline.places), self.timeline.last + 1)
        self.assertEqual(len(self.timeline.moves), self.timeline.last + 1)
        self.assertEqual(self.timeline.moves[0], [])

    def test_last_frame_has_every_drone_at_the_end(self) -> None:
        for place in self.timeline.places[-1].values():
            self.assertIs(place.zone, self.graph.end)

    def test_drone_in_transit_has_a_connection_and_no_zone(self) -> None:
        place = self.timeline.places[1][1]
        self.assertIsNone(place.zone)
        self.assertIsNotNone(place.connection)
        self.assertEqual(place.key, "s-r")
        self.assertEqual(self.timeline.moves[1], ["D1-s-r", "D2-s-r"])

    def test_place_key_is_the_zone_name(self) -> None:
        self.assertEqual(self.timeline.places[0][1].key, "s")


if __name__ == "__main__":
    unittest.main()