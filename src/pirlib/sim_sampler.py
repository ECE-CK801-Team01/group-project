"""
SimSampler — drop-in replacement for PirSampler that fakes motion without GPIO.

WHY THIS EXISTS
---------------
PirSampler.__init__ constructs a DigitalInputDevice immediately, so producer.py
cannot run on any machine that does not have a real PIR wired. To support
multiple "virtual bins" in the project demo (one real PIR, several simulated
bins) we need a sampler that produces the same .read() -> bool interface but
does not touch hardware.

DESIGN
------
SimSampler.read() returns True with a probability derived from the current
time of day, using the same hourly base-rate model as Lab 09's train_model.py
and the lab11 demo data generator. Busy at lunch, calm at night, weekends
quiet. This makes virtual bins behave like realistic activity sources rather
than uniform noise.

HIGH HOLD-OFF
-------------
When a probabilistic draw produces motion, the sampler returns True for the
next `hold_seconds` (default 1.5s) so the downstream PirInterpreter — which
requires sustained HIGH via min_high_s — can see consecutive True samples.
This mirrors a real HC-SR501 which holds OUT HIGH for its TIME-pot hold-off
period after motion. Without this, isolated random Trues never satisfy
min_high and no events fire.

ACTIVITY SCALE
--------------
Different virtual bins can be made busier or quieter by passing
activity_scale: a multiplier on the base rate. 1.0 = default; 0.5 = half as
busy; 2.0 = twice as busy. Useful for "bin-02 is high-traffic, bin-03 is
low-traffic" demos.
"""

import random
import time
from datetime import datetime


def _hourly_base_rate(day_of_week: int, hour: int) -> float:
    """Events per hour, matching Lab 09 train_model.py.

    day_of_week: 0 = Monday ... 6 = Sunday
    """
    if day_of_week >= 5:        # weekend
        return 2.0
    if 8 <= hour <= 10:
        return 15.0             # morning rush
    if 11 <= hour <= 14:
        return 25.0             # lunch
    if 15 <= hour <= 17:
        return 12.0             # afternoon
    if 18 <= hour <= 20:
        return 8.0              # evening
    return 1.0                  # night


class SimSampler:
    """Drop-in replacement for PirSampler that simulates motion in software.

    Constructor signature accepts `pin` for interface compatibility with
    PirSampler, but pin is ignored (not used). This lets producer.py construct
    either sampler with the same code path apart from one if-branch.
    """

    def __init__(self, pin: int = 0, activity_scale: float = 1.0,
                 sample_interval_s: float = 0.5, hold_seconds: float = 1.5):
        self.pin = pin
        self.activity_scale = activity_scale
        self.sample_interval_s = sample_interval_s
        self.hold_seconds = hold_seconds
        self._high_until = 0.0   # monotonic clock value

    def read(self) -> bool:
        """Return True (motion) following the time-of-day rate and hold-off."""
        now_m = time.monotonic()

        # If we are still inside an existing HIGH hold-off window, keep HIGH.
        if now_m < self._high_until:
            return True

        # Otherwise, roll the dice on starting a new motion event.
        now = datetime.now()
        events_per_hour = _hourly_base_rate(now.weekday(), now.hour)
        events_per_hour *= self.activity_scale

        samples_per_hour = 3600.0 / max(self.sample_interval_s, 0.001)
        p = events_per_hour / samples_per_hour
        if p > 1.0:
            p = 1.0
        elif p < 0.0:
            p = 0.0

        if random.random() < p:
            self._high_until = now_m + self.hold_seconds
            return True
        return False
