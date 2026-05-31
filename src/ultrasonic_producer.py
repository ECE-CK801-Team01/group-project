import paho.mqtt.client as mqtt
from filllib.initerpeter import Fill_interpreter
from filllib.smapler import Ultrasonic_Sampler
from time import sleep

sampler = Ultrasonic_Sampler(trig_pin=23, echo_pin=24)

interp = Fill_interpreter(
    empty_distance_cm=12.0,
    full_distance_cm=3.0,
    smoothing_window=5,
    change_threshold_percent=5.0,
)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("localhost", 1883)
client.loop_forever()
distance = sampler.read()

if distance is None:
    print("Invalid reading")
else:
    state, event = interp.update(distance)
    print(state)

    if event:
        print("EVENT:", event)

sleep(1)

client.publish(topic="smartbin",payload=event["fill_percent"])

sampler.close()
