# red_light_core.py

from dataclasses import dataclass
from typing import Tuple, Dict

@dataclass
class RedLightConfig:
    stop_line: Tuple[Tuple[int, int], Tuple[int, int]]
    signal_state: str = "RED"
    line_threshold: int = 5


class RedLightDetector:
    def __init__(self, config: RedLightConfig):
        self.config = config
        self.last_positions: Dict[int, Tuple[int, int]] = {}

    def _line_side(self, point, line):
        (x1, y1), (x2, y2) = line
        x, y = point
        return (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)

    def check_crossing(self, track_id: int, centroid: Tuple[int, int]) -> bool:
        # Only active when RED
        if self.config.signal_state != "RED":
            return False

        if track_id not in self.last_positions:
            self.last_positions[track_id] = centroid
            return False

        prev = self.last_positions[track_id]

        prev_side = self._line_side(prev, self.config.stop_line)
        curr_side = self._line_side(centroid, self.config.stop_line)

        self.last_positions[track_id] = centroid

        # Crossing detection
        return prev_side * curr_side < 0
    