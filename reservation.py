from models import Connection, Zone


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
