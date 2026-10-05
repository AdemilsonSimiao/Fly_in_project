import heapq
from dataclasses import dataclass

from graph import Graph
from models import Connection, Zone, ZoneType


class Reservations:
    def __init__(self) -> None:
        self.zone_usage: dict[tuple[str, int], int] = {}
        self.link_usage: dict[tuple[str, str, int], int] = {}

    def zone_has_room(self, zone: Zone, time: int) -> bool:
        limit = zone.capacity_limit
        if limit is None:
            return True
        return self.zone_usage.get((zone.name, time), 0) < limit

    def link_has_room(self, connection: Connection, turn: int) -> bool:
        key = (connection.zone_a.name, connection.zone_b.name, turn)
        return self.link_usage.get(key, 0) < connection.max_link_capacity

    def reserve_zone(self, zone: Zone, time: int) -> None:
        key = (zone.name, time)
        self.zone_usage[key] = self.zone_usage.get(key, 0) + 1

    def reserve_link(self, connection: Connection, turn: int) -> None:
        key = (connection.zone_a.name, connection.zone_b.name, turn)
        self.link_usage[key] = self.link_usage.get(key, 0) + 1


@dataclass
class Step:
    time: int
    zone: Zone
    connection: Connection | None


class Scheduler:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def find_route(
        self, reservations: Reservations, horizon: int
    ) -> list[Step] | None:
        graph = self.graph
        start = (graph.start.name, 0)
        penalty: dict[tuple[str, int], int] = {start: 0}
        parent: dict[
            tuple[str, int], tuple[tuple[str, int], Connection | None]
        ] = {}
        done: set[tuple[str, int]] = set()
        counter = 0
        heap: list[tuple[int, int, int, str]] = [(0, 0, counter, start[0])]
        while heap:
            time, cost, _, name = heapq.heappop(heap)
            state = (name, time)
            if state in done:
                continue
            done.add(state)
            if name == graph.end.name:
                return self._build_route(state, parent)
            if time >= horizon:
                continue
            zone = graph.zones[name]
            options: list[tuple[Zone, int, Connection | None]] = []
            if reservations.zone_has_room(zone, time + 1):
                options.append((zone, 1, None))
            for connection in graph.get_connections(zone):
                other = connection.other_zone(zone)
                if other.zone_type is ZoneType.BLOCKED:
                    continue
                if not reservations.link_has_room(connection, time + 1):
                    continue
                if not reservations.zone_has_room(
                    other, time + other.entry_cost
                ):
                    continue
                options.append((other, other.entry_cost, connection))
            for other, duration, used in options:
                new_state = (other.name, time + duration)
                extra = 0
                if used is not None:
                    if other.zone_type is not ZoneType.PRIORITY:
                        extra = 1
                new_cost = cost + extra
                if new_state in penalty and penalty[new_state] <= new_cost:
                    continue
                penalty[new_state] = new_cost
                parent[new_state] = (state, used)
                counter += 1
                heapq.heappush(
                    heap, (new_state[1], new_cost, counter, other.name)
                )
        return None

    def _build_route(
        self,
        last: tuple[str, int],
        parent: dict[
            tuple[str, int], tuple[tuple[str, int], Connection | None]
        ],
    ) -> list[Step]:
        route: list[Step] = []
        state = last
        while state in parent:
            previous, connection = parent[state]
            route.append(
                Step(state[1], self.graph.zones[state[0]], connection)
            )
            state = previous
        route.reverse()
        return route

    def plan(self, nb_drones: int) -> list[dict[int, Zone]]:
        reservations = Reservations()
        horizon = 4 * (len(self.graph.zones) + nb_drones)
        schedule: dict[int, dict[int, Zone]] = {}
        last_turn = 0
        for drone_id in range(1, nb_drones + 1):
            route = self.find_route(reservations, horizon)
            if route is None:
                raise ValueError(f"no schedule found for drone D{drone_id}")
            previous_time = 0
            for step in route:
                if step.connection is None:
                    reservations.reserve_zone(step.zone, step.time)
                else:
                    turn = previous_time + 1
                    reservations.reserve_link(step.connection, turn)
                    reservations.reserve_zone(step.zone, step.time)
                    schedule.setdefault(turn, {})[drone_id] = step.zone
                previous_time = step.time
            last_turn = max(last_turn, previous_time)
        return [schedule.get(turn, {}) for turn in range(1, last_turn + 1)]
