from dataclasses import dataclass

from graph import Graph
from models import Connection, Drone, Zone, ZoneType


class SimulationError(Exception):
    pass


@dataclass
class Departure:
    drone: Drone
    origin: Zone
    destination: Zone
    connection: Connection


class Simulation:
    def __init__(self, graph: Graph, nb_drones: int) -> None:
        self.graph = graph
        self.turn = 0
        self.drones: dict[int, Drone] = {
            number: Drone(number, current_zone=graph.start)
            for number in range(1, nb_drones + 1)
        }

    def is_finished(self) -> bool:
        return all(
            drone.current_zone is self.graph.end
            for drone in self.drones.values()
        )

    def step(self, moves: dict[int, Zone]) -> list[str]:
        departures = self._check_moves(moves)
        arriving = [
            drone for drone in self.drones.values()
            if drone.current_connection is not None
        ]
        self._check_zone_capacity(departures, arriving)
        self._check_link_capacity(departures)
        return self._apply(departures, arriving)

    def _check_moves(self, moves: dict[int, Zone]) -> list[Departure]:
        departures: list[Departure] = []
        for drone_id, destination in moves.items():
            drone = self.drones.get(drone_id)
            if drone is None:
                raise SimulationError(f"unknown drone D{drone_id}")
            origin = drone.current_zone
            if origin is None:
                raise SimulationError(
                    f"D{drone_id} is in transit and cannot get a new move"
                )
            if origin is self.graph.end:
                raise SimulationError(f"D{drone_id} is already delivered")
            if destination.zone_type is ZoneType.BLOCKED:
                raise SimulationError(
                    f"D{drone_id} cannot enter blocked zone "
                    f"'{destination.name}'"
                )
            connection = self.graph.get_connections_zones(
                origin, destination
            )
            if connection is None:
                raise SimulationError(
                    f"D{drone_id}: '{origin.name}' and "
                    f"'{destination.name}' are not connected"
                )
            departures.append(
                Departure(drone, origin, destination, connection)
            )
        return departures

    def _check_zone_capacity(
        self, departures: list[Departure], arriving: list[Drone]
    ) -> None:
        occupancy: dict[str, int] = {}
        for drone in self.drones.values():
            if drone.current_zone is not None:
                name = drone.current_zone.name
                occupancy[name] = occupancy.get(name, 0) + 1
        for departure in departures:
            occupancy[departure.origin.name] -= 1
            if departure.destination.entry_cost == 1:
                name = departure.destination.name
                occupancy[name] = occupancy.get(name, 0) + 1
        for drone in arriving:
            if drone.transit_destination is None:
                raise SimulationError(f"D{drone.drone_id} has no destination")
            name = drone.transit_destination.name
            occupancy[name] = occupancy.get(name, 0) + 1
        for name, count in occupancy.items():
            limit = self.graph.zones[name].capacity_limit
            if limit is not None and count > limit:
                raise SimulationError(
                    f"turn {self.turn + 1}: zone '{name}' would hold "
                    f"{count} drones (maximum {limit})"
                )

    def _check_link_capacity(self, departures: list[Departure]) -> None:
        usage: dict[tuple[str, str], int] = {}
        for departure in departures:
            connection = departure.connection
            key = (connection.zone_a.name, connection.zone_b.name)
            usage[key] = usage.get(key, 0) + 1
            if usage[key] > connection.max_link_capacity:
                raise SimulationError(
                    f"turn {self.turn + 1}: connection "
                    f"'{key[0]}-{key[1]}' would carry {usage[key]} drones "
                    f"(maximum {connection.max_link_capacity})"
                )

    def _apply(
        self, departures: list[Departure], arriving: list[Drone]
    ) -> list[str]:
        tokens: list[tuple[int, str]] = []
        for drone in arriving:
            destination = drone.transit_destination
            if destination is None:
                raise SimulationError(f"D{drone.drone_id} has no destination")
            drone.current_zone = destination
            drone.current_connection = None
            drone.transit_destination = None
            drone.transit_turns_left = 0
            tokens.append(
                (drone.drone_id, f"D{drone.drone_id}-{destination.name}")
            )
        for departure in departures:
            drone = departure.drone
            destination = departure.destination
            if destination.entry_cost > 1:
                connection = departure.connection
                drone.current_zone = None
                drone.current_connection = connection
                drone.transit_destination = destination
                drone.transit_turns_left = destination.entry_cost - 1
                label = f"{connection.zone_a.name}-{connection.zone_b.name}"
            else:
                drone.current_zone = destination
                label = destination.name
            tokens.append((drone.drone_id, f"D{drone.drone_id}-{label}"))
        self.turn += 1
        return [text for _, text in sorted(tokens)]