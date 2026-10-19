import os
import tempfile
import unittest

from engine import Simulation, SimulationError
from graph import Graph
from parser import parse_map


class EngineTestCase(unittest.TestCase):
    line = (
        "nb_drones: 3\n"
        "start_hub: s 0 0\n"
        "end_hub: g 3 0\n"
        "hub: a 1 0\n"
        "hub: b 2 0\n"
        "hub: x 0 1 [zone=blocked]\n"
        "connection: s-a\n"
        "connection: a-b\n"
        "connection: b-g\n"
        "connection: s-x\n"
    )
    restricted = (
        "nb_drones: 2\n"
        "start_hub: s 0 0\n"
        "end_hub: g 3 0\n"
        "hub: r 1 0 [zone=restricted]\n"
        "hub: m 2 0\n"
        "connection: s-r\n"
        "connection: r-m\n"
        "connection: m-g\n"
    )
    wide = (
        "nb_drones: 3\n"
        "start_hub: s 0 0\n"
        "end_hub: g 3 0\n"
        "hub: a 1 0 [max_drones=2]\n"
        "connection: s-a [max_link_capacity=3]\n"
        "connection: a-g [max_link_capacity=3]\n"
        "connection: s-g [max_link_capacity=3]\n"
    )

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def build(self, text: str) -> Simulation:
        path = os.path.join(self.directory.name, "map.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        data = parse_map(path)
        return Simulation(Graph(data), data.nb_drones)

    def move(self, sim: Simulation, moves: dict[int, str]) -> list[str]:
        zones = {
            drone_id: sim.graph.zones[name]
            for drone_id, name in moves.items()
        }
        return sim.step(zones)

    def zone_of(self, sim: Simulation, drone_id: int) -> str | None:
        zone = sim.drones[drone_id].current_zone
        return None if zone is None else zone.name


class TestInitialState(EngineTestCase):
    def test_drones_start_in_the_start_zone(self) -> None:
        sim = self.build(self.line)
        self.assertEqual(sorted(sim.drones), [1, 2, 3])
        for drone_id in sim.drones:
            self.assertEqual(self.zone_of(sim, drone_id), "s")

    def test_starts_at_turn_zero_and_not_finished(self) -> None:
        sim = self.build(self.line)
        self.assertEqual(sim.turn, 0)
        self.assertFalse(sim.is_finished())


class TestBasicMovement(EngineTestCase):
    def test_single_move(self) -> None:
        sim = self.build(self.line)
        self.assertEqual(self.move(sim, {1: "a"}), ["D1-a"])
        self.assertEqual(self.zone_of(sim, 1), "a")
        self.assertEqual(self.zone_of(sim, 2), "s")
        self.assertEqual(sim.turn, 1)

    def test_waiting_drones_are_not_in_the_output(self) -> None:
        sim = self.build(self.line)
        self.assertEqual(self.move(sim, {}), [])
        self.assertEqual(sim.turn, 1)

    def test_output_is_sorted_by_drone_id(self) -> None:
        sim = self.build(self.wide)
        output = self.move(sim, {3: "g", 1: "a", 2: "g"})
        self.assertEqual(output, ["D1-a", "D2-g", "D3-g"])

    def test_column_advances_in_a_single_turn(self) -> None:
        sim = self.build(self.line)
        self.move(sim, {1: "a"})
        self.move(sim, {1: "b", 2: "a"})
        output = self.move(sim, {1: "g", 2: "b", 3: "a"})
        self.assertEqual(output, ["D1-g", "D2-b", "D3-a"])

    def test_full_run_finishes(self) -> None:
        sim = self.build(self.line)
        self.move(sim, {1: "a"})
        self.move(sim, {1: "b", 2: "a"})
        self.move(sim, {1: "g", 2: "b", 3: "a"})
        self.move(sim, {2: "g", 3: "b"})
        self.assertFalse(sim.is_finished())
        self.move(sim, {3: "g"})
        self.assertTrue(sim.is_finished())
        self.assertEqual(sim.turn, 5)


class TestInvalidMoves(EngineTestCase):
    def test_blocked_zone(self) -> None:
        sim = self.build(self.line)
        with self.assertRaises(SimulationError):
            self.move(sim, {1: "x"})

    def test_zones_not_connected(self) -> None:
        sim = self.build(self.line)
        with self.assertRaises(SimulationError):
            self.move(sim, {1: "g"})

    def test_unknown_drone(self) -> None:
        sim = self.build(self.line)
        with self.assertRaises(SimulationError):
            self.move(sim, {9: "a"})

    def test_delivered_drone_cannot_move_again(self) -> None:
        sim = self.build(self.wide)
        self.move(sim, {1: "g"})
        with self.assertRaises(SimulationError):
            self.move(sim, {1: "a"})

    def test_error_leaves_the_state_untouched(self) -> None:
        sim = self.build(self.line)
        with self.assertRaises(SimulationError):
            self.move(sim, {1: "a", 2: "a"})
        self.assertEqual(sim.turn, 0)
        for drone_id in sim.drones:
            self.assertEqual(self.zone_of(sim, drone_id), "s")


class TestCapacity(EngineTestCase):
    def test_zone_with_capacity_one(self) -> None:
        sim = self.build(self.line)
        with self.assertRaises(SimulationError) as context:
            self.move(sim, {1: "a", 2: "a"})
        self.assertIn("zone 'a'", str(context.exception))

    def test_moving_into_an_occupied_zone(self) -> None:
        sim = self.build(self.line)
        self.move(sim, {1: "a"})
        with self.assertRaises(SimulationError):
            self.move(sim, {2: "a"})

    def test_zone_with_max_drones_two(self) -> None:
        sim = self.build(self.wide)
        self.move(sim, {1: "a", 2: "a"})
        with self.assertRaises(SimulationError):
            self.move(sim, {3: "a"})

    def test_end_zone_has_no_limit(self) -> None:
        sim = self.build(self.wide)
        self.move(sim, {1: "g", 2: "g", 3: "g"})
        self.assertTrue(sim.is_finished())

    def test_start_zone_has_no_limit(self) -> None:
        sim = self.build(self.wide)
        self.move(sim, {1: "a"})
        self.move(sim, {1: "s"})
        self.assertEqual(self.zone_of(sim, 1), "s")

    def test_link_capacity_one(self) -> None:
        sim = self.build(self.line)
        self.move(sim, {1: "a"})
        self.move(sim, {1: "b", 2: "a"})
        with self.assertRaises(SimulationError):
            self.move(sim, {1: "a", 2: "b"})

    def test_link_capacity_is_respected_when_larger(self) -> None:
        sim = self.build(self.wide)
        self.move(sim, {1: "g", 2: "g", 3: "g"})
        self.assertTrue(sim.is_finished())

    def test_link_capacity_exceeded(self) -> None:
        text = self.wide.replace(
            "connection: s-g [max_link_capacity=3]",
            "connection: s-g [max_link_capacity=2]",
        )
        sim = self.build(text)
        with self.assertRaises(SimulationError) as context:
            self.move(sim, {1: "g", 2: "g", 3: "g"})
        self.assertIn("connection 's-g'", str(context.exception))


class TestRestrictedZone(EngineTestCase):
    def test_crossing_takes_two_turns(self) -> None:
        sim = self.build(self.restricted)
        self.assertEqual(self.move(sim, {1: "r"}), ["D1-s-r"])
        self.assertIsNone(sim.drones[1].current_zone)
        self.assertIsNotNone(sim.drones[1].current_connection)
        self.assertEqual(self.move(sim, {}), ["D1-r"])
        self.assertEqual(self.zone_of(sim, 1), "r")
        self.assertIsNone(sim.drones[1].current_connection)
        self.assertIsNone(sim.drones[1].transit_destination)

    def test_drone_in_transit_cannot_get_a_new_move(self) -> None:
        sim = self.build(self.restricted)
        self.move(sim, {1: "r"})
        with self.assertRaises(SimulationError):
            self.move(sim, {1: "m"})

    def test_connection_is_freed_when_the_drone_arrives(self) -> None:
        sim = self.build(self.restricted)
        self.move(sim, {1: "r"})
        self.assertEqual(self.move(sim, {2: "r"}), ["D1-r", "D2-s-r"])
        self.assertEqual(self.move(sim, {1: "m"}), ["D1-m", "D2-r"])

    def test_connection_is_busy_during_the_start_turn(self) -> None:
        sim = self.build(self.restricted)
        with self.assertRaises(SimulationError):
            self.move(sim, {1: "r", 2: "r"})

    def test_subject_example_total_turns(self) -> None:
        sim = self.build(self.restricted)
        self.move(sim, {1: "r"})
        self.move(sim, {2: "r"})
        self.move(sim, {1: "m"})
        self.move(sim, {1: "g", 2: "m"})
        self.move(sim, {2: "g"})
        self.assertTrue(sim.is_finished())
        self.assertEqual(sim.turn, 5)

    def test_arrival_in_a_full_zone_is_rejected(self) -> None:
        sim = self.build(
            self.restricted.replace(
                "hub: r 1 0 [zone=restricted]",
                "hub: r 1 0 [zone=restricted]\nhub: q 1 1",
            ) + "connection: s-q\nconnection: q-r\n"
        )
        self.move(sim, {1: "r", 2: "q"})
        self.move(sim, {2: "r"})
        self.assertEqual(self.zone_of(sim, 1), "r")
        with self.assertRaises(SimulationError) as context:
            self.move(sim, {})
        self.assertIn("zone 'r'", str(context.exception))


if __name__ == "__main__":
    unittest.main()