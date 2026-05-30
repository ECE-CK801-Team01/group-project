from time import sleep
from smapler import Ultrasonic_Sampler
from initerpeter import Fill_interpreter


sampler = Ultrasonic_Sampler(trig_pin=23, echo_pin=24)

interp = Fill_interpreter(
    empty_distance_cm=12.0,
    full_distance_cm=3.0,
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
