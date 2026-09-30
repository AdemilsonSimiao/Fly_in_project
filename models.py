from dataclasses import dataclass, field
from enum import Enum


class ZoneType(Enum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


@dataclass
class Zone:
    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1
    is_start: bool = False
    is_end: bool = False

    @property
    def capacity_limit(self) -> int | None:
        if self.is_start or self.is_end:
            return None
        return self.max_drones

    @property
    def entry_cost(self) -> int:
        if self.zone_type is ZoneType.RESTRICTED:
            return 2
        return 1


@dataclass
class Connection:
    zone_a: Zone
    zone_b: Zone
    max_link_capacity: int = 1

    def other_zone(self, zone: Zone) -> Zone:
        if zone is self.zone_a:
            return self.zone_b
        if zone is self.zone_b:
            return self.zone_a
        raise ValueError("Zone is not an endpoint of this connection")


@dataclass
class Drone:
    drone_id: int
    current_zone: Zone | None = None
    current_connection: Connection | None = None
    transit_destination: Zone | None = None
    transit_turns_left: int = 0
    route: list[Zone] = field(default_factory=list)
