import glob
import os
import unittest

from graph import Graph
from models import Connection, Zone, ZoneType
from parser import MapData, parse_map


class GraphTestCase(unittest.TestCase):
    def build(
        self,
        links: list[tuple[str, str]],
        blocked: tuple[str, ...] = (),
        restricted: tuple[str, ...] = (),
    ) -> Graph:
        zones: dict[str, Zone] = {}
        for name in ("s", "a", "b", "c", "g"):
            zone_type = ZoneType.NORMAL
            if name in blocked:
                zone_type = ZoneType.BLOCKED
            elif name in restricted:
                zone_type = ZoneType.RESTRICTED
            zones[name] = Zone(
                name=name,
                x=0,
                y=0,
                zone_type=zone_type,
                is_start=name == "s",
                is_end=name == "g",
            )
        connections = [
            Connection(zones[first], zones[second], 2)
            for first, second in links
        ]
        return Graph(MapData(1, zones, connections, zones["s"], zones["g"]))

    def names(self, zones: list[Zone]) -> list[str]:
        return sorted(zone.name for zone in zones)


class TestAdjacency(GraphTestCase):
    def test_connection_works_in_both_directions(self) -> None:
        graph = self.build([("s", "a")])
        from_s = graph.get_neighbors(graph.zones["s"])
        from_a = graph.get_neighbors(graph.zones["a"])
        self.assertEqual(self.names(from_s), ["a"])
        self.assertEqual(self.names(from_a), ["s"])

    def test_zone_without_connections(self) -> None:
        graph = self.build([("s", "a")])
        self.assertEqual(graph.get_neighbors(graph.zones["c"]), [])
        self.assertEqual(graph.get_connections(graph.zones["c"]), [])

    def test_several_neighbors(self) -> None:
        graph = self.build([("s", "a"), ("s", "b"), ("s", "c")])
        neighbors = graph.get_neighbors(graph.zones["s"])
        self.assertEqual(self.names(neighbors), ["a", "b", "c"])

    def test_blocked_zones_are_not_neighbors(self) -> None:
        graph = self.build([("s", "a"), ("s", "b")], blocked=("b",))
        neighbors = graph.get_neighbors(graph.zones["s"])
        self.assertEqual(self.names(neighbors), ["a"])

    def test_restricted_zones_are_neighbors(self) -> None:
        graph = self.build([("s", "a")], restricted=("a",))
        neighbors = graph.get_neighbors(graph.zones["s"])
        self.assertEqual(self.names(neighbors), ["a"])


class TestConnectionLookup(GraphTestCase):
    def test_finds_connection_in_both_orders(self) -> None:
        graph = self.build([("s", "a")])
        first = graph.get_connections_zones(graph.zones["s"], graph.zones["a"])
        second = graph.get_connections_zones(graph.zones["a"], graph.zones["s"])
        self.assertIsNotNone(first)
        self.assertIs(first, second)

    def test_returns_none_when_not_connected(self) -> None:
        graph = self.build([("s", "a")])
        result = graph.get_connections_zones(graph.zones["s"], graph.zones["g"])
        self.assertIsNone(result)

    def test_get_connections_keeps_capacity(self) -> None:
        graph = self.build([("s", "a"), ("a", "g")])
        connections = graph.get_connections(graph.zones["a"])
        self.assertEqual(len(connections), 2)
        for connection in connections:
            self.assertEqual(connection.max_link_capacity, 2)


class TestPathToDestination(GraphTestCase):
    def test_direct_path(self) -> None:
        graph = self.build([("s", "g")])
        self.assertTrue(graph.path_destination())

    def test_longer_path(self) -> None:
        graph = self.build([("s", "a"), ("a", "b"), ("b", "g")])
        self.assertTrue(graph.path_destination())

    def test_path_through_restricted_zone(self) -> None:
        graph = self.build([("s", "a"), ("a", "g")], restricted=("a",))
        self.assertTrue(graph.path_destination())

    def test_no_connections(self) -> None:
        graph = self.build([])
        self.assertFalse(graph.path_destination())

    def test_end_in_another_component(self) -> None:
        graph = self.build([("s", "a"), ("b", "g")])
        self.assertFalse(graph.path_destination())

    def test_only_path_is_blocked(self) -> None:
        graph = self.build(
            [("s", "a"), ("a", "g")], blocked=("a",)
        )
        self.assertFalse(graph.path_destination())

    def test_blocked_end(self) -> None:
        graph = self.build([("s", "g")], blocked=("g",))
        self.assertFalse(graph.path_destination())

    def test_detour_around_blocked_zone(self) -> None:
        graph = self.build(
            [("s", "a"), ("a", "g"), ("s", "b"), ("b", "g")],
            blocked=("a",),
        )
        self.assertTrue(graph.path_destination())

    def test_cycle_doesnt_loop_forever(self) -> None:
        graph = self.build([("s", "a"), ("a", "b"), ("b", "s")])
        self.assertFalse(graph.path_destination())

    def test_cycle_with_exit(self) -> None:
        graph = self.build(
            [("s", "a"), ("a", "b"), ("b", "s"), ("b", "g")]
        )
        self.assertTrue(graph.path_destination())


class TestProjectMaps(unittest.TestCase):
    def test_all_project_(self) -> None:
        folder = os.path.dirname(os.path.abspath(__file__))
        paths = glob.glob(os.path.join(folder, "maps", "*", "*.txt"))
        for path in paths:
            with self.subTest(path=path):
                graph = Graph(parse_map(path))
                self.assertTrue(graph.path_destination())


if __name__ == "__main__":
    unittest.main()