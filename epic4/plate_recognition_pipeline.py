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
    # debounce.py

class DetectionDebouncer:
    def __init__(self, cooldown_frames: int = 30):
        self.cooldown_frames = cooldown_frames
        self.last_trigger_frame = {}

    def is_allowed(self, track_id: int, current_frame: int) -> bool:
        last_frame = self.last_trigger_frame.get(track_id, -9999)

        if current_frame - last_frame >= self.cooldown_frames:
            self.last_trigger_frame[track_id] = current_frame
            return True

        return False
    # red_light_pipeline.py

from red_light_core import RedLightConfig, RedLightDetector
from debounce import DetectionDebouncer


class RedLightPipeline:
    def __init__(self):
        self.config = RedLightConfig(
            stop_line=((200, 500), (1000, 500)),
            signal_state="RED"
        )

        self.detector = RedLightDetector(self.config)
        self.debouncer = DetectionDebouncer(cooldown_frames=30)

    def process(self, track_id, centroid, frame_number):
        crossed = self.detector.check_crossing(track_id, centroid)

        if crossed and self.debouncer.is_allowed(track_id, frame_number):
            return {
                "track_id": track_id,
                "violation": "RED_LIGHT",
                "frame": frame_number
            }

        return None