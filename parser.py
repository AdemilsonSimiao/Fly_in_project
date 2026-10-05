from dataclasses import dataclass
from models import Connection, Zone, ZoneType


class ParseError(Exception):
    def __init__(self, line_number: int | None, message: str) -> None:
        if line_number is None:
            super().__init__(message)
        else:
            super().__init__(f"line {line_number}: {message}")


@dataclass
class MapData:
    nb_drones: int
    zones: dict[str, Zone]
    connections: list[Connection]
    start: Zone
    end: Zone


def read_map_lines(path: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    try:
        with open(path, encoding="utf-8") as file:
            for number, raw in enumerate(file, start=1):
                text = raw.strip()
                if text and not text.startswith("#"):
                    lines.append((number, text))
    except (OSError, UnicodeDecodeError) as error:
        raise ParseError(None, f"cannot read '{path}': {error}") from None
    return lines


def parse_int(text: str, line_number: int, what: str) -> int:
    try:
        return int(text)
    except ValueError:
        raise ParseError(
            line_number, f"{what} must be an integer, got '{text}'"
        ) from None


def parse_positive(text: str, line_number: int, what: str) -> int:
    value = parse_int(text, line_number, what)
    if value < 1:
        raise ParseError(
            line_number, f"{what} must be a positive integer, got {value}"
        )
    return value


def split_line(text: str, line_number: int) -> tuple[str, str]:
    prefix, separator, body = text.partition(":")
    if not separator:
        raise ParseError(line_number, f"missing ':' in '{text}'")
    return prefix.strip(), body.strip()


def parse_metadata(text: str, line_number: int) -> dict[str, str]:
    text = text.strip()
    result: dict[str, str] = {}
    if not text:
        return result
    if not (text.startswith("[") and text.endswith("]")):
        raise ParseError(
            line_number, "metadata must be enclosed in brackets [...]"
        )
    for item in text[1:-1].split():
        key, separator, value = item.partition("=")
        if not separator or not key or not value:
            raise ParseError(
                line_number,
                f"invalid metadata '{item}' (expected key=value)",
            )
        if key in result:
            raise ParseError(line_number, f"duplicate metadata '{key}'")
        result[key] = value
    return result


def parse_zone(prefix: str, body: str, line_number: int) -> Zone:
    head, bracket, tail = body.partition("[")
    fields = head.split()
    if len(fields) != 3:
        raise ParseError(
            line_number, f"expected '{prefix}: <name> <x> <y> [metadata]'"
        )
    name = fields[0]
    if "-" in name:
        raise ParseError(
            line_number, f"zone name '{name}' must not contain dashes"
        )
    x = parse_int(fields[1], line_number, "x coordinate")
    y = parse_int(fields[2], line_number, "y coordinate")
    metadata = parse_metadata(bracket + tail, line_number)
    zone_type = ZoneType.NORMAL
    color: str | None = None
    max_drones = 1
    for key, value in metadata.items():
        if key == "zone":
            try:
                zone_type = ZoneType(value)
            except ValueError:
                raise ParseError(
                    line_number,
                    f"invalid zone type '{value}' "
                    "(expected: normal, blocked, restricted, priority)",
                ) from None
        elif key == "color":
            color = value
        elif key == "max_drones":
            if prefix == "hub":
                max_drones = parse_positive(value, line_number, key)
            else:
                max_drones = parse_int(value, line_number, key)
        else:
            raise ParseError(
                line_number, f"unknown zone metadata '{key}'"
            )
    return Zone(
        name=name,
        x=x,
        y=y,
        zone_type=zone_type,
        color=color,
        max_drones=max_drones,
        is_start=prefix == "start_hub",
        is_end=prefix == "end_hub",
    )


def parse_connection(
    body: str, line_number: int, zones: dict[str, Zone]
) -> Connection:
    head, bracket, tail = body.partition("[")
    fields = head.split()
    if len(fields) != 1:
        raise ParseError(
            line_number,
            "expected 'connection: <zone1>-<zone2> [metadata]'",
        )
    names = fields[0].split("-")
    if len(names) != 2 or not names[0] or not names[1]:
        raise ParseError(
            line_number,
            f"invalid connection '{fields[0]}' "
            "(expected exactly one '-' between two zone names)",
        )
    for name in names:
        if name not in zones:
            raise ParseError(line_number, f"unknown zone '{name}'")
    if names[0] == names[1]:
        raise ParseError(
            line_number, f"zone '{names[0]}' cannot connect to itself"
        )
    metadata = parse_metadata(bracket + tail, line_number)
    capacity = 1
    for key, value in metadata.items():
        if key == "max_link_capacity":
            capacity = parse_positive(value, line_number, key)
        else:
            raise ParseError(
                line_number, f"unknown connection metadata '{key}'"
            )
    return Connection(zones[names[0]], zones[names[1]], capacity)


def parse_map(path: str) -> MapData:
    lines = read_map_lines(path)
    if not lines:
        raise ParseError(None, "map file is empty")
    first_number, first_text = lines[0]
    prefix, body = split_line(first_text, first_number)
    if prefix != "nb_drones":
        raise ParseError(
            first_number, "the first line must be 'nb_drones: <number>'"
        )
    nb_drones = parse_positive(body, first_number, "nb_drones")
    zones: dict[str, Zone] = {}
    connections: list[Connection] = []
    links: set[frozenset[str]] = set()
    start: Zone | None = None
    end: Zone | None = None
    for number, text in lines[1:]:
        prefix, body = split_line(text, number)
        if prefix in ("hub", "start_hub", "end_hub"):
            zone = parse_zone(prefix, body, number)
            if zone.name in zones:
                raise ParseError(number, f"duplicate zone '{zone.name}'")
            if zone.is_start:
                if start is not None:
                    raise ParseError(number, "duplicate start_hub")
                start = zone
            if zone.is_end:
                if end is not None:
                    raise ParseError(number, "duplicate end_hub")
                end = zone
            zones[zone.name] = zone
        elif prefix == "connection":
            connection = parse_connection(body, number, zones)
            key = frozenset(
                (connection.zone_a.name, connection.zone_b.name)
            )
            if key in links:
                raise ParseError(
                    number,
                    f"duplicate connection "
                    f"'{connection.zone_a.name}-{connection.zone_b.name}'",
                )
            links.add(key)
            connections.append(connection)
        elif prefix == "nb_drones":
            raise ParseError(number, "nb_drones must appear only once")
        else:
            raise ParseError(number, f"unknown line type '{prefix}'")
    if start is None:
        raise ParseError(None, "missing start_hub")
    if end is None:
        raise ParseError(None, "missing end_hub")
    return MapData(nb_drones, zones, connections, start, end)
