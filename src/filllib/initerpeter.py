from collections import deque
from statistics import median
from typing import Optional
from smapler import Ultrasonic_Sampler

class Fill_interpreter(object):
    def __init__(self,empty_distance_cm:float,full_distance_cm:float,smoothing_window:int = 5, change_threshold_percent: float = 5.0):
        if empty_distance_cm <= full_distance_cm:
            raise ValueError("NO GOOD")
        if smoothing_window <= 0:
            raise ValueError("SOmething")
        
        self.empty_distance_cm = empty_distance_cm
        self.full_distance_cm = full_distance_cm
        self.smoothing_window = smoothing_window
        self.change_threshold_percent = change_threshold_percent

        self.samples = deque(maxlen=smoothing_window)
        self.last_fill_percent:Optional[float] = None
        self.last_fill_state:Optional[str] = None

    def distance_to_fill_percent(self, distance_cm: float) -> float:
        fill = 100.0 * (
            (self.empty_distance_cm - distance_cm)
            / (self.empty_distance_cm - self.full_distance_cm)
        )

        if fill < 0:
            return 0.0

        if fill > 100:
            return 100.0

        return fill

    def classify(self, fill_percent: float) -> str:
        if fill_percent < 9:
            return "empty"
        if fill_percent < 33:
            return "low"
        if fill_percent < 67:
            return "medium"
        if fill_percent < 90:
            return "high"
        return "full"

    def update(self, distance_cm: float) -> tuple[dict, Optional[dict]]:
        """
        Process one distance measurement.

        Returns:
            state_payload:
                current fill-level state, useful for MQTT retained state / HA

            event_payload:
                only emitted when the fill level changes meaningfully
        """

        self.samples.append(distance_cm)

        smoothed_distance = median(self.samples)
        fill_percent = self.distance_to_fill_percent(smoothed_distance)
        fill_state = self.classify(fill_percent)

        state_payload = {
            "distance_cm": round(smoothed_distance, 2),
            "fill_percent": round(fill_percent, 1),
            "fill_state": fill_state,
            "sample_count": len(self.samples),
            "smoothing_window": self.smoothing_window,
        }

        should_emit_event = False
        reason = None

        if self.last_fill_percent is None:
            should_emit_event = True
            reason = "initial_reading"

        elif abs(fill_percent - self.last_fill_percent) >= self.change_threshold_percent:
            should_emit_event = True
            reason = "fill_percent_changed"

        elif fill_state != self.last_fill_state:
            should_emit_event = True
            reason = "fill_state_changed"

        event_payload = None

        if should_emit_event:
            event_payload = {
                **state_payload,
                "reason": reason,
                "previous_fill_percent": (
                    None if self.last_fill_percent is None else round(self.last_fill_percent, 1)
                ),
                "previous_fill_state": self.last_fill_state,
            }

            self.last_fill_percent = fill_percent
            self.last_fill_state = fill_state

        return state_payload, event_payload
