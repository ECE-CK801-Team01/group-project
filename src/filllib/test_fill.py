from time import sleep
from smapler import UltrasonicSampler
from initerpeter import FillInterpreter


sampler = UltrasonicSampler(trig_pin=23, echo_pin=24)

interp = FillInterpreter(
    empty_distance_cm=40.0,
    full_distance_cm=8.0,
    smoothing_window=5,
    change_threshold_percent=5.0,
)

print("Reading HC-SR04. Press Ctrl-C to stop.")

try:
    while True:
        distance = sampler.read()

        if distance is None:
            print("Invalid reading")
        else:
            state, event = interp.update(distance)
            print(state)

            if event:
                print("EVENT:", event)

        sleep(1)

except KeyboardInterrupt:
    print("\nStopping.")

finally:
    sampler.close()
