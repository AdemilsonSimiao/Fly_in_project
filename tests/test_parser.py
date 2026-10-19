import glob
import os
import tempfile
import unittest
from models import ZoneType
from parser import ParseError, parse_map


class ParserTestCase(unittest.TestCase):
    base = "nb_drones: 2\nstart_hub: s 0 0\nend_hub: g 1 0\n"

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def write_map(self, content: str) -> str:
        path = os.path.join(self.directory.name, "map.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write(content)
        return path

    def assert_error(self, content: str, expected: str) -> None:
        path = self.write_map(content)
        with self.assertRaises(ParseError) as context:
            parse_map(path)
        self.assertIn(expected, str(context.exception))


class TestValidMaps(ParserTestCase):
    def test_simple_map(self) -> None:
        data = parse_map(self.write_map(
            "# comment\n"
            "nb_drones: 3\n"
            "\n"
            "start_hub: s 0 0 [color=green]\n"
            "hub: a 1 -1 [zone=restricted color=red max_drones=2]\n"
            "end_hub: g 2 0\n"
            "connection: s-a\n"
            "connection: a-g [max_link_capacity=2]\n"
        ))
        self.assertEqual(data.nb_drones, 3)
        self.assertEqual(len(data.zones), 3)
        self.assertEqual(len(data.connections), 2)
        self.assertEqual(data.start.name, "s")
        self.assertEqual(data.end.name, "g")
        self.assertTrue(data.start.is_start)
        self.assertTrue(data.end.is_end)

    def test_zone_defaults(self) -> None:
        data = parse_map(self.write_map(self.base + "hub: a 2 0\n"))
        zone = data.zones["a"]
        self.assertIs(zone.zone_type, ZoneType.NORMAL)
        self.assertIsNone(zone.color)
        self.assertEqual(zone.max_drones, 1)

    def test_zone_metadata(self) -> None:
        data = parse_map(self.write_map(
            self.base
            + "hub: a -2 -3 [max_drones=4 color=blue zone=priority]\n"
        ))
        zone = data.zones["a"]
        self.assertEqual((zone.x, zone.y), (-2, -3))
        self.assertIs(zone.zone_type, ZoneType.PRIORITY)
        self.assertEqual(zone.color, "blue")
        self.assertEqual(zone.max_drones, 4)

    def test_connection_capacity(self) -> None:
        data = parse_map(self.write_map(
            self.base + "connection: s-g\n"
        ))
        self.assertEqual(data.connections[0].max_link_capacity, 1)
        data = parse_map(self.write_map(
            self.base + "connection: s-g [max_link_capacity=3]\n"
        ))
        self.assertEqual(data.connections[0].max_link_capacity, 3)

    def test_same_zone_objects(self) -> None:
        data = parse_map(self.write_map(self.base + "connection: s-g\n"))
        connection = data.connections[0]
        self.assertIs(connection.zone_a, data.start)
        self.assertIs(connection.zone_b, data.end)

    def test_ignore_max_drones(self) -> None:
        data = parse_map(self.write_map(
            "nb_drones: 1\n"
            "start_hub: s 0 0 [max_drones=5]\n"
            "end_hub: g 1 0 [max_drones=2]\n"
        ))
        self.assertIsNone(data.start.capacity_limit)
        self.assertIsNone(data.end.capacity_limit)

    def test_disconnected_map(self) -> None:
        data = parse_map(self.write_map(self.base))
        self.assertEqual(data.connections, [])

    def test_project_maps(self) -> None:
        folder = os.path.dirname(os.path.abspath(__file__))
        paths = glob.glob(os.path.join(folder, "maps", "*", "*.txt"))
        for path in paths:
            with self.subTest(path=path):
                data = parse_map(path)
                self.assertGreater(data.nb_drones, 0)


class TestNbDrones(ParserTestCase):
    def test_empty_file(self) -> None:
        self.assert_error("", "empty")

    def test_must_be_first_line(self) -> None:
        self.assert_error(
            "start_hub: s 0 0\nnb_drones: 1\n", "first line"
        )

    def test_must_be_positive(self) -> None:
        self.assert_error("nb_drones: 0\n", "positive")

    def test_must_be_integer(self) -> None:
        self.assert_error("nb_drones: two\n", "integer")

    def test_only_once(self) -> None:
        self.assert_error(self.base + "nb_drones: 3\n", "only once")


class TestZoneErrors(ParserTestCase):
    def test_invalid_zone(self) -> None:
        self.assert_error(self.base + "hub: a 2 0 [zone=foo]\n", "zone type")

    def test_invalid_coordinate(self) -> None:
        self.assert_error(self.base + "hub: a x 0\n", "integer")

    def test_missing_coordinate(self) -> None:
        self.assert_error(self.base + "hub: a 2\n", "expected")

    def test_dash_in_name(self) -> None:
        self.assert_error(self.base + "hub: a-b 2 0\n", "dashes")

    def test_duplicate_zone(self) -> None:
        self.assert_error(self.base + "hub: s 2 0\n", "duplicate zone")

    def test_duplicate_start(self) -> None:
        self.assert_error(self.base + "start_hub: t 5 5\n", "duplicate start")

    def test_duplicate_end(self) -> None:
        self.assert_error(self.base + "end_hub: t 5 5\n", "duplicate end")

    def test_missing_start(self) -> None:
        self.assert_error("nb_drones: 1\nend_hub: g 0 0\n", "start_hub")

    def test_missing_end(self) -> None:
        self.assert_error("nb_drones: 1\nstart_hub: s 0 0\n", "end_hub")

    def test_invalid_max_drones(self) -> None:
        for value in ("0", "-1", "abc"):
            with self.subTest(value=value):
                self.assert_error(
                    self.base + f"hub: a 2 0 [max_drones={value}]\n",
                    "max_drones",
                )

    def test_unknown_metadata(self) -> None:
        self.assert_error(self.base + "hub: a 2 0 [speed=3]\n", "unknown")

    def test_without_closing_bracket(self) -> None:
        self.assert_error(self.base + "hub: a 2 0 [color=red\n", "brackets")

    def test_without_value(self) -> None:
        self.assert_error(self.base + "hub: a 2 0 [color]\n", "key=value")

    def test_duplicate_metadata(self) -> None:
        self.assert_error(
            self.base + "hub: a 2 0 [color=red color=blue]\n", "duplicate"
        )


class TestConnectionErrors(ParserTestCase):
    def test_unknown_zone(self) -> None:
        self.assert_error(self.base + "connection: s-zzz\n", "unknown zone")

    def test_zone_defined(self) -> None:
        self.assert_error(
            self.base + "connection: s-a\nhub: a 2 0\n", "unknown zone"
        )

    def test_duplicate_connection(self) -> None:
        self.assert_error(
            self.base + "connection: s-g\nconnection: g-s\n", "duplicate"
        )

    def test_self_connection(self) -> None:
        self.assert_error(self.base + "connection: s-s\n", "itself")

    def test_too_many_dashes(self) -> None:
        self.assert_error(
            self.base + "connection: s-g-x\n", "invalid connection"
        )

    def test_invalid_link(self) -> None:
        for value in ("0", "-2", "abc"):
            with self.subTest(value=value):
                self.assert_error(
                    self.base
                    + f"connection: s-g [max_link_capacity={value}]\n",
                    "max_link_capacity",
                )

    def test_unknown_metadata(self) -> None:
        self.assert_error(self.base + "connection: s-g [speed=1]\n", "unknown")


class TestGeneralErrors(ParserTestCase):
    def test_unknown_line_type(self) -> None:
        self.assert_error(self.base + "foo: bar\n", "unknown line type")

    def test_missing_colon(self) -> None:
        self.assert_error(self.base + "hub a 2 0\n", "':'")

    def test_line_number(self) -> None:
        self.assert_error(
            "# comment\nnb_drones: 1\nstart_hub: s 0 0\nend_hub: g x 0\n",
            "line 4",
        )

    def test_missing_file(self) -> None:
        with self.assertRaises(ParseError):
            parse_map(os.path.join(self.directory.name, "nope.txt"))


if __name__ == "__main__":
    unittest.main()
