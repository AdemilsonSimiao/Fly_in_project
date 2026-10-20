import math
import tkinter as tk

from errors import WindowError
from graph import Graph
from models import Connection, Zone, ZoneType
from timeline import Place, Timeline

Point = tuple[float, float]


class Window:
    background = "#1b1e27"
    edge = "#4b5263"
    active = "#ffd54f"
    default_fill = "#546e7a"
    light = "#eceff1"
    dark = "#10131a"
    muted = "#90a4ae"
    named = {"lime": "#32cd32"}
    turn_ms = 700
    frame_ms = 16

    def __init__(self, graph: Graph, timeline: Timeline) -> None:
        self.graph = graph
        self.timeline = timeline
        self.turn = 0
        self.progress = 1.0
        self.playing = False
        self.job: str | None = None
        self.hover = ""
        self.scale = 1.0
        self.radius = 10.0
        self.points: dict[str, Point] = {}
        self.colors: dict[str, str] = {}
        zones = graph.zones.values()
        self.min_x = min(zone.x for zone in zones)
        self.max_x = max(zone.x for zone in zones)
        self.min_y = min(zone.y for zone in zones)
        self.max_y = max(zone.y for zone in zones)
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            raise WindowError(f"cannot open a window: {error}") from None
        self.root.title("Fly-in")
        self.root.minsize(600, 420)
        self.root.configure(bg=self.background)
        self.speed = tk.DoubleVar(value=1.0)
        self.canvas = tk.Canvas(
            self.root,
            width=1000,
            height=600,
            bg=self.background,
            highlightthickness=0,
        )
        self.info = self.make_label(self.muted)
        self.status = self.make_label(self.light)
        self.play_button = self.build_controls()
        self.canvas.pack(fill="both", expand=True)
        self.bind_events()
        self.root.update_idletasks()
        self.draw()

    def make_label(self, color: str) -> tk.Label:
        label = tk.Label(self.root, bg=self.background, fg=color, anchor="w")
        label.pack(side="bottom", fill="x", padx=12, pady=(0, 6))
        return label

    def build_controls(self) -> tk.Button:
        bar = tk.Frame(self.root, bg=self.background)
        bar.pack(side="bottom", fill="x", padx=10, pady=6)
        tk.Button(bar, text="Restart", command=self.restart).pack(side="left")
        tk.Button(bar, text="Back", command=self.back).pack(
            side="left", padx=4
        )
        play = tk.Button(bar, text="Play", width=6, command=self.toggle)
        play.pack(side="left")
        tk.Button(bar, text="Next", command=self.advance).pack(
            side="left", padx=4
        )
        tk.Label(bar, text="Speed", bg=self.background, fg=self.light).pack(
            side="left", padx=(16, 4)
        )
        tk.Scale(
            bar,
            variable=self.speed,
            from_=0.25,
            to=4.0,
            resolution=0.25,
            orient="horizontal",
            length=160,
            bg=self.background,
            fg=self.light,
            highlightthickness=0,
        ).pack(side="left")
        return play

    def bind_events(self) -> None:
        self.canvas.bind("<Configure>", lambda _: self.draw())
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", lambda _: self.set_hover(""))
        self.root.bind("<space>", lambda _: self.toggle())
        self.root.bind("<Right>", lambda _: self.advance())
        self.root.bind("<Left>", lambda _: self.back())
        self.root.bind("r", lambda _: self.restart())
        self.root.bind("<Escape>", lambda _: self.root.destroy())

    def run(self) -> None:
        self.root.after(500, self.toggle)
        self.root.mainloop()

    def duration(self) -> float:
        return self.turn_ms / max(0.1, self.speed.get())

    def refresh_button(self) -> None:
        self.play_button.config(text="Pause" if self.playing else "Play")

    def schedule_tick(self) -> None:
        if self.job is None:
            self.job = self.root.after(self.frame_ms, self.tick)

    def stop(self) -> None:
        self.playing = False
        if self.job is not None:
            self.root.after_cancel(self.job)
            self.job = None
        self.refresh_button()

    def tick(self) -> None:
        self.job = None
        if self.progress < 1.0:
            step = self.frame_ms / self.duration()
            self.progress = min(1.0, self.progress + step)
        elif self.playing and self.turn < self.timeline.last:
            self.turn += 1
            self.progress = 0.0
        else:
            self.playing = False
            self.refresh_button()
        self.draw()
        if self.playing or self.progress < 1.0:
            self.schedule_tick()

    def toggle(self) -> None:
        if self.playing:
            self.stop()
            return
        if self.turn == self.timeline.last and self.progress >= 1.0:
            self.restart()
        self.playing = True
        self.refresh_button()
        self.schedule_tick()

    def restart(self) -> None:
        self.stop()
        self.turn = 0
        self.progress = 1.0
        self.draw()

    def back(self) -> None:
        self.stop()
        self.turn = max(0, self.turn - 1)
        self.progress = 1.0
        self.draw()

    def advance(self) -> None:
        if self.progress < 1.0:
            self.progress = 1.0
            self.draw()
        elif self.turn < self.timeline.last:
            self.turn += 1
            self.progress = 0.0
            self.draw()
            self.schedule_tick()

    def on_motion(self, event: "tk.Event[tk.Misc]") -> None:
        for zone in self.graph.zones.values():
            x, y = self.points[zone.name]
            if math.hypot(event.x - x, event.y - y) <= self.radius:
                self.set_hover(self.describe(zone))
                return
        self.set_hover("")

    def set_hover(self, text: str) -> None:
        self.hover = text
        self.update_info()

    def describe(self, zone: Zone) -> str:
        text = f"{zone.name} ({zone.zone_type.value})"
        if zone.capacity_limit is not None:
            text += f", max {zone.max_drones} drones"
        places = self.timeline.places[self.turn]
        here = sorted(n for n, place in places.items() if place.zone is zone)
        if zone.is_start or zone.is_end:
            return f"{text}, {len(here)} drones"
        if here:
            text += ": " + " ".join(f"D{number}" for number in here)
        return text

    def update_info(self) -> None:
        moves = " ".join(self.timeline.moves[self.turn])
        wrap = max(self.canvas.winfo_width() - 24, 200)
        self.info.config(
            text=self.hover or moves, wraplength=wrap, justify="left"
        )

    def update_status(self) -> None:
        total = len(self.timeline.places[0])
        delivered = self.counted(self.graph.end)
        self.status.config(
            text=(
                f"Turn {self.turn}/{self.timeline.last}"
                f"     delivered {delivered}/{total}"
            )
        )
        self.update_info()

    def counted(self, zone: Zone) -> int:
        index = self.turn
        if zone.is_end and self.progress < 1.0 and self.turn > 0:
            index = self.turn - 1
        places = self.timeline.places[index]
        return sum(1 for place in places.values() if place.zone is zone)

    def color_of(self, name: str | None) -> str:
        if name is None:
            return self.default_fill
        name = self.named.get(name, name)
        if name not in self.colors:
            try:
                self.root.winfo_rgb(name)
                self.colors[name] = name
            except tk.TclError:
                self.colors[name] = self.default_fill
        return self.colors[name]

    def text_on(self, fill: str) -> str:
        red, green, blue = self.root.winfo_rgb(fill)
        brightness = (0.299 * red + 0.587 * green + 0.114 * blue) / 65535
        return self.dark if brightness > 0.6 else self.light

    def layout(self) -> None:
        width = max(self.canvas.winfo_width(), 200)
        height = max(self.canvas.winfo_height(), 200)
        margin = 70
        real_x = self.max_x - self.min_x
        real_y = self.max_y - self.min_y
        self.scale = max(
            10.0,
            min(
                (width - 2 * margin) / max(1, real_x),
                (height - 2 * margin) / max(1, real_y),
                150.0,
            ),
        )
        left = (width - real_x * self.scale) / 2
        top = (height - real_y * self.scale) / 2
        self.points = {
            name: (
                left + (zone.x - self.min_x) * self.scale,
                top + (zone.y - self.min_y) * self.scale,
            )
            for name, zone in self.graph.zones.items()
        }
        self.radius = max(7.0, min(22.0, self.scale * 0.3))

    def draw(self) -> None:
        self.canvas.delete("all")
        self.layout()
        self.draw_connections()
        self.draw_zones()
        self.draw_drones()
        self.draw_legend()
        self.update_status()

    def transit_connections(self) -> list[Connection]:
        frames = [self.timeline.places[self.turn]]
        if self.progress < 1.0 and self.turn > 0:
            frames.append(self.timeline.places[self.turn - 1])
        return [
            place.connection
            for frame in frames
            for place in frame.values()
            if place.connection is not None
        ]

    def draw_connections(self) -> None:
        busy = self.transit_connections()
        for connection in self.graph.connections:
            x1, y1 = self.points[connection.zone_a.name]
            x2, y2 = self.points[connection.zone_b.name]
            live = any(connection is other for other in busy)
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=self.active if live else self.edge,
                width=min(1 + connection.max_link_capacity, 6),
            )

    def zone_style(self, zone: Zone) -> tuple[str, int, tuple[int, ...]]:
        if zone.zone_type is ZoneType.PRIORITY:
            return self.active, 4, ()
        if zone.zone_type is ZoneType.RESTRICTED:
            return "#ff8a65", 3, (5, 3)
        if zone.zone_type is ZoneType.BLOCKED:
            return "#e57373", 2, ()
        return "#cfd8dc", 2, ()

    def draw_zones(self) -> None:
        radius = self.radius
        for zone in self.graph.zones.values():
            x, y = self.points[zone.name]
            fill = self.color_of(zone.color)
            outline, width, dash = self.zone_style(zone)
            if zone.zone_type is ZoneType.BLOCKED:
                fill = "#2b2f3a"
            self.canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill=fill,
                outline=outline,
                width=width,
                dash=dash,
            )
            if zone.zone_type is ZoneType.BLOCKED:
                near = radius * 0.5
                self.canvas.create_line(
                    x - near, y - near, x + near, y + near, fill=outline
                )
                self.canvas.create_line(
                    x - near, y + near, x + near, y - near, fill=outline
                )
            if zone.is_start or zone.is_end:
                self.draw_counter(zone, x, y, fill)
            if len(zone.name) * 6.5 <= self.scale:
                self.canvas.create_text(
                    x,
                    y + radius + 10,
                    text=zone.name,
                    fill=self.muted,
                    font=("Helvetica", 8),
                )

    def draw_counter(self, zone: Zone, x: float, y: float, fill: str) -> None:
        size = max(8, int(self.radius * 0.7))
        self.canvas.create_text(
            x,
            y,
            text=str(self.counted(zone)),
            fill=self.text_on(fill),
            font=("Helvetica", size, "bold"),
        )
        self.canvas.create_text(
            x,
            y - self.radius - 10,
            text="START" if zone.is_start else "GOAL",
            fill=self.light,
            font=("Helvetica", 8, "bold"),
        )

    def draw_legend(self) -> None:
        height = max(self.canvas.winfo_height(), 200)
        self.canvas.create_text(
            12,
            height - 10,
            anchor="sw",
            fill=self.muted,
            font=("Helvetica", 8),
            text=(
                "gold ring = priority   dashed = restricted   "
                "X = blocked   thick line = more capacity   "
                "hover a zone for details"
            ),
        )

    @staticmethod
    def ease(value: float) -> float:
        return value * value * (3 - 2 * value)

    def anchor(self, place: Place, offset: Point) -> Point:
        if place.zone is not None:
            x, y = self.points[place.zone.name]
        elif place.connection is not None:
            x1, y1 = self.points[place.connection.zone_a.name]
            x2, y2 = self.points[place.connection.zone_b.name]
            x, y = (x1 + x2) / 2, (y1 + y2) / 2
        else:
            raise WindowError("a drone has no position")
        return x + offset[0], y + offset[1]

    def offsets(
        self, places: dict[int, Place], spacing: float
    ) -> dict[int, Point]:
        result: dict[int, Point] = {}
        groups: dict[str, list[int]] = {}
        for number, place in places.items():
            zone = place.zone
            if zone is not None and (zone.is_start or zone.is_end):
                result[number] = (0.0, 0.0)
            else:
                groups.setdefault(place.key, []).append(number)
        for numbers in groups.values():
            columns = math.ceil(math.sqrt(len(numbers)))
            rows = math.ceil(len(numbers) / columns)
            for index, number in enumerate(sorted(numbers)):
                row, column = divmod(index, columns)
                result[number] = (
                    (column - (columns - 1) / 2) * spacing,
                    (row - (rows - 1) / 2) * spacing,
                )
        return result

    def parked(self, origin: Place, target: Place) -> bool:
        zone = origin.zone
        if zone is None or zone is not target.zone:
            return False
        return zone.is_start or zone.is_end

    def draw_drones(self) -> None:
        after = self.timeline.places[self.turn]
        animating = self.progress < 1.0 and self.turn > 0
        before = self.timeline.places[self.turn - 1] if animating else after
        ratio = self.ease(self.progress) if animating else 1.0
        size = max(3.5, self.radius * 0.45)
        offsets_before = self.offsets(before, size * 2.3)
        offsets_after = self.offsets(after, size * 2.3)
        for number, target in after.items():
            origin = before[number]
            if self.parked(origin, target):
                continue
            x1, y1 = self.anchor(origin, offsets_before[number])
            x2, y2 = self.anchor(target, offsets_after[number])
            x = x1 + (x2 - x1) * ratio
            y = y1 + (y2 - y1) * ratio
            self.canvas.create_oval(
                x - size,
                y - size,
                x + size,
                y + size,
                fill="#ffffff",
                outline=self.dark,
                width=2,
            )
            if size >= 8:
                self.canvas.create_text(
                    x,
                    y,
                    text=str(number),
                    fill=self.dark,
                    font=("Helvetica", int(size * 0.9), "bold"),
                )
