from dataclasses import dataclass
from engine import Simulation
from graph import Graph
from models import Connection, Zone


@dataclass
class Place:
    zone: Zone | None
    connection: Connection | None

    @property
    def key(self) -> str:
        if self.zone is not None:
            return self.zone.name
        if self.connection is not None:
            first = self.connection.zone_a.name
            return f"{first}-{self.connection.zone_b.name}"
        return ""


class Timeline:
    def __init__(
        self,
        graph: Graph,
        nb_drones: int,
        schedule: list[dict[int, Zone]],
    ) -> None:
        simulation = Simulation(graph, nb_drones)
        self.places: list[dict[int, Place]] = [self.snapshot(simulation)]
        self.moves: list[list[str]] = [[]]
        for turn_moves in schedule:
            self.moves.append(simulation.step(turn_moves))
            self.places.append(self.snapshot(simulation))

    @property
    def last(self) -> int:
        return len(self.places) - 1

    def snapshot(self, simulation: Simulation) -> dict[int, Place]:
        return {
            number: Place(drone.current_zone, drone.current_connection)
            for number, drone in simulation.drones.items()
        }
