import unittest
from models import Zone, ZoneType, Drone, Connection


class TestZone(unittest.TestCase):
    def test_values(self) -> None:
        zone = Zone(name="hub", x=2, y=3)
        self.assertIs(zone.zone_type, ZoneType.NORMAL)
        self.assertIsNone(zone.color)
        self.assertEqual(zone.max_drones, 1)
        self.assertEqual(zone.capacity_limit, 1)
        self.assertEqual(zone.entry_cost, 1)

    def test_unlimited_capacity(self) -> None:
        start = Zone(name="start", x=0, y=0, is_start=True)
        end = Zone(name="goal", x=5, y=5, is_end=True)
        self.assertIsNone(start.capacity_limit)
        self.assertIsNone(end.capacity_limit)

    def test_restrict_zone(self) -> None:
        zone = Zone(
            name="tunnel",
            x=1,
            y=1,
            zone_type=ZoneType.RESTRICTED,
        )
        self.assertEqual(zone.entry_cost, 2)

    def test_other_zone(self) -> None:
        for zone_type in (
            ZoneType.NORMAL,
            ZoneType.BLOCKED,
            ZoneType.PRIORITY,
        ):
            with self.subTest(zone_type=zone_type):
                zone = Zone(name="hub", x=0, y=0, zone_type=zone_type)
                self.assertEqual(zone.entry_cost, 1)


class TestConnection(unittest.TestCase):
    def test_returns_opposite(self) -> None:
        zone_a = Zone(name="a", x=0, y=0)
        zone_b = Zone(name="b", x=1, y=0)
        connection = Connection(zone_a, zone_b)
        self.assertIs(connection.other_zone(zone_a), zone_b)
        self.assertIs(connection.other_zone(zone_b), zone_a)

    def test_rejects_unconnected(self) -> None:
        zone_a = Zone(name="a", x=0, y=0)
        zone_b = Zone(name="b", x=1, y=0)
        unconnected = Zone(name="c", x=2, y=0)
        connection = Connection(zone_a, zone_b)
        with self.assertRaises(ValueError):
            connection.other_zone(unconnected)


class TestDrone(unittest.TestCase):
    def test_default_values(self) -> None:
        drone = Drone(drone_id=1)
        self.assertEqual(drone.drone_id, 1)
        self.assertEqual(drone.transit_turns_left, 0)
        self.assertEqual(drone.route, [])
        self.assertIsNone(drone.current_zone)
        self.assertIsNone(drone.current_connection)
        self.assertIsNone(drone.transit_destination)

    def test_route_not_shared(self) -> None:
        first_drone = Drone(drone_id=1)
        second_drone = Drone(drone_id=2)
        first_drone.route.append(Zone(name="hub", x=0, y=0))
        self.assertEqual(len(first_drone.route), 1)
        self.assertEqual(second_drone.route, [])


if __name__ == "__main__":
    unittest.main()
