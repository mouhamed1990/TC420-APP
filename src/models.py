"""
Data models for TC420 LED Controller GUI.
"""
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class TimePoint:
    """A single point on the timeline: time (minutes from midnight) + brightness (0-100)."""
    time_minutes: int  # 0-1439 (00:00 to 23:59)
    brightness: int    # 0-100

    @property
    def hours(self) -> int:
        return self.time_minutes // 60

    @property
    def minutes(self) -> int:
        return self.time_minutes % 60

    @property
    def time_str(self) -> str:
        return f"{self.hours:02d}:{self.minutes:02d}"

    @classmethod
    def from_hm(cls, hours: int, minutes: int, brightness: int) -> 'TimePoint':
        return cls(time_minutes=hours * 60 + minutes, brightness=brightness)

    def to_dict(self) -> dict:
        return {"time_minutes": self.time_minutes, "brightness": self.brightness}

    @classmethod
    def from_dict(cls, data: dict) -> 'TimePoint':
        return cls(time_minutes=data["time_minutes"], brightness=data["brightness"])


@dataclass
class ChannelProgram:
    """Schedule for a single channel: ordered list of TimePoints (max 50)."""
    points: List[TimePoint] = field(default_factory=list)
    name: str = ""

    MAX_POINTS = 50

    def add_point(self, time_minutes: int, brightness: int) -> Optional[TimePoint]:
        if len(self.points) >= self.MAX_POINTS:
            return None
        tp = TimePoint(time_minutes=time_minutes, brightness=brightness)
        self.points.append(tp)
        self.sort()
        return tp

    def remove_point(self, index: int):
        if 0 <= index < len(self.points):
            self.points.pop(index)

    def sort(self):
        self.points.sort(key=lambda p: p.time_minutes)

    def get_brightness_at(self, time_minutes: int) -> int:
        """Interpolate brightness at a given time."""
        if not self.points:
            return 0

        # Before first point or after last point: wrap around
        if time_minutes <= self.points[0].time_minutes:
            return self.points[0].brightness
        if time_minutes >= self.points[-1].time_minutes:
            return self.points[-1].brightness

        # Find surrounding points and interpolate
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i + 1]
            if p1.time_minutes <= time_minutes <= p2.time_minutes:
                if p2.time_minutes == p1.time_minutes:
                    return p1.brightness
                ratio = (time_minutes - p1.time_minutes) / (p2.time_minutes - p1.time_minutes)
                return int(p1.brightness + ratio * (p2.brightness - p1.brightness))

        return 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "points": [p.to_dict() for p in self.points]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ChannelProgram':
        return cls(
            name=data.get("name", ""),
            points=[TimePoint.from_dict(p) for p in data.get("points", [])]
        )


# Channel color definitions
CHANNEL_COLORS = [
    "#00d4ff",  # Channel 1 - Aqua/Cyan
    "#ff6b6b",  # Channel 2 - Coral/Red
    "#51cf66",  # Channel 3 - Lime/Green
    "#be4bdb",  # Channel 4 - Violet/Purple
    "#ffd43b",  # Channel 5 - Gold/Yellow
]

CHANNEL_NAMES = [
    "Channel 1",
    "Channel 2",
    "Channel 3",
    "Channel 4",
    "Channel 5",
]

NUM_CHANNELS = 5
NUM_MODES = 50


@dataclass
class ModeProgram:
    """A complete mode with 5 channel programs."""
    name: str = "Mode"
    channels: List[ChannelProgram] = field(default_factory=list)

    def __post_init__(self):
        while len(self.channels) < NUM_CHANNELS:
            self.channels.append(ChannelProgram(name=CHANNEL_NAMES[len(self.channels)]))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "channels": [ch.to_dict() for ch in self.channels]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ModeProgram':
        mode = cls(name=data.get("name", "Mode"))
        mode.channels = [ChannelProgram.from_dict(ch) for ch in data.get("channels", [])]
        while len(mode.channels) < NUM_CHANNELS:
            mode.channels.append(ChannelProgram(name=CHANNEL_NAMES[len(mode.channels)]))
        return mode


@dataclass
class DeviceState:
    """Current state of the TC420 device."""
    connected: bool = False
    device_time: Optional[str] = None
    firmware_version: Optional[str] = None
    active_mode: int = 0  # 0-3


@dataclass
class AppState:
    """Full application state with all 4 modes."""
    modes: List[ModeProgram] = field(default_factory=list)
    active_mode_index: int = 0
    device: DeviceState = field(default_factory=DeviceState)

    def __post_init__(self):
        while len(self.modes) < NUM_MODES:
            self.modes.append(ModeProgram(name=f"Mode {len(self.modes) + 1}"))

    @property
    def active_mode(self) -> ModeProgram:
        return self.modes[self.active_mode_index]

    def to_dict(self) -> dict:
        return {
            "modes": [m.to_dict() for m in self.modes],
            "active_mode_index": self.active_mode_index,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AppState':
        state = cls()
        state.modes = [ModeProgram.from_dict(m) for m in data.get("modes", [])]
        state.active_mode_index = data.get("active_mode_index", 0)
        while len(state.modes) < NUM_MODES:
            state.modes.append(ModeProgram(name=f"Mode {len(state.modes) + 1}"))
        return state
