from collections import deque
from models import Connection, Zone, ZoneType
from parser import MapData


class Graph:
    def __init__(self, data: MapData) -> None:
        self.zones: dict[str, Zone] = data.zones
        self.start: Zone = data.start
        self.end: Zone = data.end
        self.connections: list[Connection] = data.connections
        self.adjacent: dict[str, list[Connection]] = {
            name: [] for name in data.zones
        }
        self.links: dict[frozenset[str], Connection] = {}
        for connection in data.connections:
            name_a = connection.zone_a.name
            name_b = connection.zone_b.name
            self.adjacent[name_a].append(connection)
            self.adjacent[name_b].append(connection)
            self.links[frozenset((name_a, name_b))] = connection

    def get_connections(self, zone: Zone) -> list[Connection]:
        return self.adjacent[zone.name]

    def get_connections_zones(
        self,
        zone_a: Zone,
        zone_b: Zone
    ) -> Connection | None:
        return self.links.get(frozenset((zone_a.name, zone_b.name)))

    def get_neighbors(self, zone: Zone) -> list[Zone]:
        neighbors: list[Zone] = []
        for connection in self.adjacent[zone.name]:
            other = connection.other_zone(zone)
            if other.zone_type is not ZoneType.BLOCKED:
                neighbors.append(other)
        return neighbors

    def path_destination(self) -> bool:
        visited: set[str] = {self.start.name}
        queue: deque[Zone] = deque([self.start])
        while queue:
            current = queue.popleft()
            if current is self.end:
                return True
            for neighbor in self.get_neighbors(current):
                if neighbor.name not in visited:
                    visited.add(neighbor.name)
                    queue.append(neighbor)
        return False
