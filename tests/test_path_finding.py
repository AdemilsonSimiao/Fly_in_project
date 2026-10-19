import glob
import os
import tempfile
import unittest

from engine import Simulation
from graph import Graph
from models import Connection, Zone
from parser import MapData, parse_map
from path_finding import Reservations, Scheduler


class SchedulerTestCase(unittest.TestCase):
    line = (
        "nb_drones: 2\n"
        "start_hub: s 0 0\n"
        "end_hub: g 3 0\n"
        "hub: a 1 0\n"
        "hub: b 2 0\n"
        "connection: s-a\n"
        "connection: a-b\n"
        "connection: b-g\n"
    )
    restricted = (
        "nb_drones: 1\n"
        "start_hub: s 0 0\n"
        "end_hub: g 2 0\n"
        "hub: r 1 0 [zone=restricted]\n"
        "connection: s-r\n"
        "connection: r-g\n"
    )

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def load(self, text: str) -> MapData:
        path = os.path.join(self.directory.name, "map.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write(text)
        return parse_map(path)

    def scheduler(self, text: str) -> Scheduler:
        return Scheduler(Graph(self.load(text)))

    def zone(self, scheduler: Scheduler, name: str) -> Zone:
        return scheduler.graph.zones[name]

    def connection(self, scheduler: Scheduler, first: str, second: str
                   ) -> Connection:
        found = scheduler.graph.get_connections_zones(
            self.zone(scheduler, first), self.zone(scheduler, second)
        )
        assert found is not None
        return found

    def run_schedule(
        self, scheduler: Scheduler, schedule: list[dict[int, Zone]],
        nb_drones: int,
    ) -> Simulation:
        sim = Simulation(scheduler.graph, nb_drones)
        for moves in schedule:
            sim.step(moves)
        return sim


class TestReservations(SchedulerTestCase):
    def test_zone_with_capacity_one(self) -> None:
        scheduler = self.scheduler(self.line)
        zone = self.zone(scheduler, "a")
        reservations = Reservations()
        self.assertTrue(reservations.zone_has_room(zone, 1))
        reservations.reserve_zone(zone, 1)
        self.assertFalse(reservations.zone_has_room(zone, 1))

    def test_other_instants_are_independent(self) -> None:
        scheduler = self.scheduler(self.line)
        zone = self.zone(scheduler, "a")
        reservations = Reservations()
        reservations.reserve_zone(zone, 1)
        self.assertTrue(reservations.zone_has_room(zone, 2))

    def test_zone_with_larger_capacity(self) -> None:
        text = self.line.replace(
            "hub: a 1 0", "hub: a 1 0 [max_drones=2]"
        )
        scheduler = self.scheduler(text)
        zone = self.zone(scheduler, "a")
        reservations = Reservations()
        reservations.reserve_zone(zone, 1)
        self.assertTrue(reservations.zone_has_room(zone, 1))
        reservations.reserve_zone(zone, 1)
        self.assertFalse(reservations.zone_has_room(zone, 1))

    def test_start_and_end_have_no_limit(self) -> None:
        scheduler = self.scheduler(self.line)
        reservations = Reservations()
        for name in ("s", "g"):
            zone = self.zone(scheduler, name)
            for _ in range(5):
                reservations.reserve_zone(zone, 1)
            self.assertTrue(reservations.zone_has_room(zone, 1))

    def test_link_capacity(self) -> None:
        scheduler = self.scheduler(self.line)
        link = self.connection(scheduler, "s", "a")
        reservations = Reservations()
        self.assertTrue(reservations.link_has_room(link, 1))
        reservations.reserve_link(link, 1)
        self.assertFalse(reservations.link_has_room(link, 1))
        self.assertTrue(reservations.link_has_room(link, 2))

    def test_link_with_larger_capacity(self) -> None:
        text = self.line.replace(
            "connection: s-a", "connection: s-a [max_link_capacity=2]"
        )
        scheduler = self.scheduler(text)
        link = self.connection(scheduler, "s", "a")
        reservations = Reservations()
        reservations.reserve_link(link, 1)
        self.assertTrue(reservations.link_has_room(link, 1))
        reservations.reserve_link(link, 1)
        self.assertFalse(reservations.link_has_room(link, 1))


class TestFindRoute(SchedulerTestCase):
    def test_straight_route(self) -> None:
        scheduler = self.scheduler(self.line)
        route = scheduler.find_route(Reservations(), 20)
        assert route is not None
        self.assertEqual(
            [(step.time, step.zone.name) for step in route],
            [(1, "a"), (2, "b"), (3, "g")],
        )

    def test_waits_when_a_zone_is_reserved(self) -> None:
        scheduler = self.scheduler(self.line)
        reservations = Reservations()
        reservations.reserve_zone(self.zone(scheduler, "a"), 1)
        route = scheduler.find_route(reservations, 20)
        assert route is not None
        self.assertIsNone(route[0].connection)
        self.assertEqual(route[0].zone.name, "s")
        self.assertEqual(route[-1].time, 4)

    def test_waits_when_a_link_is_reserved(self) -> None:
        scheduler = self.scheduler(self.line)
        reservations = Reservations()
        reservations.reserve_link(self.connection(scheduler, "s", "a"), 1)
        route = scheduler.find_route(reservations, 20)
        assert route is not None
        self.assertEqual(route[-1].time, 4)

    def test_restricted_zone_takes_two_turns(self) -> None:
        scheduler = self.scheduler(self.restricted)
        route = scheduler.find_route(Reservations(), 20)
        assert route is not None
        self.assertEqual(
            [(step.time, step.zone.name) for step in route],
            [(2, "r"), (3, "g")],
        )

    def test_blocked_zone_is_avoided(self) -> None:
        text = (
            "nb_drones: 1\n"
            "start_hub: s 0 0\n"
            "end_hub: g 3 0\n"
            "hub: x 1 0 [zone=blocked]\n"
            "hub: a 1 1\n"
            "hub: b 2 1\n"
            "connection: s-x\n"
            "connection: x-g\n"
            "connection: s-a\n"
            "connection: a-b\n"
            "connection: b-g\n"
        )
        scheduler = self.scheduler(text)
        route = scheduler.find_route(Reservations(), 20)
        assert route is not None
        names = [step.zone.name for step in route]
        self.assertNotIn("x", names)
        self.assertEqual(names, ["a", "b", "g"])

    def test_priority_zone_wins_a_tie(self) -> None:
        text = (
            "nb_drones: 1\n"
            "start_hub: s 0 0\n"
            "end_hub: g 2 0\n"
            "hub: a 1 1\n"
            "hub: b 1 -1 [zone=priority]\n"
            "connection: s-a\n"
            "connection: s-b\n"
            "connection: a-g\n"
            "connection: b-g\n"
        )
        scheduler = self.scheduler(text)
        route = scheduler.find_route(Reservations(), 20)
        assert route is not None
        self.assertEqual(route[0].zone.name, "b")

    def test_no_path_returns_none(self) -> None:
        text = (
            "nb_drones: 1\n"
            "start_hub: s 0 0\n"
            "end_hub: g 3 0\n"
            "hub: a 1 0\n"
            "connection: s-a\n"
        )
        scheduler = self.scheduler(text)
        self.assertIsNone(scheduler.find_route(Reservations(), 10))


class TestPlan(SchedulerTestCase):
    def test_two_drones_in_a_line(self) -> None:
        scheduler = self.scheduler(self.line)
        schedule = scheduler.plan(2)
        self.assertEqual(len(schedule), 4)
        sim = self.run_schedule(scheduler, schedule, 2)
        self.assertTrue(sim.is_finished())
        self.assertEqual(sim.turn, 4)

    def test_schedule_only_lists_departures(self) -> None:
        scheduler = self.scheduler(self.restricted)
        schedule = scheduler.plan(1)
        self.assertEqual(len(schedule), 3)
        self.assertEqual(list(schedule[0]), [1])
        self.assertEqual(schedule[0][1].name, "r")
        self.assertEqual(schedule[1], {})
        self.assertEqual(schedule[2][1].name, "g")

    def test_restricted_schedule_is_valid(self) -> None:
        scheduler = self.scheduler(self.restricted)
        sim = self.run_schedule(scheduler, scheduler.plan(1), 1)
        self.assertTrue(sim.is_finished())

    def test_drones_share_two_paths(self) -> None:
        text = (
            "nb_drones: 2\n"
            "start_hub: s 0 0\n"
            "end_hub: g 2 0\n"
            "hub: a 1 1\n"
            "hub: b 1 -1\n"
            "connection: s-a\n"
            "connection: s-b\n"
            "connection: a-g\n"
            "connection: b-g\n"
        )
        scheduler = self.scheduler(text)
        schedule = scheduler.plan(2)
        self.assertEqual(len(schedule), 2)

    def test_many_drones_through_one_corridor(self) -> None:
        text = self.line.replace("nb_drones: 2", "nb_drones: 10")
        scheduler = self.scheduler(text)
        schedule = scheduler.plan(10)
        self.assertEqual(len(schedule), 12)
        sim = self.run_schedule(scheduler, schedule, 10)
        self.assertTrue(sim.is_finished())

    def test_unreachable_end_raises(self) -> None:
        text = (
            "nb_drones: 1\n"
            "start_hub: s 0 0\n"
            "end_hub: g 3 0\n"
            "hub: a 1 0\n"
            "connection: s-a\n"
        )
        scheduler = self.scheduler(text)
        with self.assertRaises(ValueError):
            scheduler.plan(1)


class TestProjectMaps(SchedulerTestCase):
    optimum = {
        "01_linear_path": 4,
        "02_simple_fork": 4,
        "03_basic_capacity": 4,
        "01_dead_end_trap": 8,
        "02_circular_loop": 10,
        "03_priority_puzzle": 6,
        "01_maze_nightmare": 13,
        "02_capacity_hell": 16,
        "03_ultimate_challenge": 26,
        "01_the_impossible_dream": 43,
    }

    def test_every_map_reaches_the_optimum(self) -> None:
        folder = os.path.dirname(os.path.abspath(__file__))
        paths = glob.glob(os.path.join(folder, "maps", "*", "*.txt"))
        for path in paths:
            name = os.path.basename(path)[:-4]
            with self.subTest(map=name):
                data = parse_map(path)
                scheduler = Scheduler(Graph(data))
                schedule = scheduler.plan(data.nb_drones)
                sim = self.run_schedule(scheduler, schedule, data.nb_drones)
                self.assertTrue(sim.is_finished())
                self.assertEqual(sim.turn, self.optimum[name])


if __name__ == "__main__":
    unittest.main()
