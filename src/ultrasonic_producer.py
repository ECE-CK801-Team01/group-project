# import paho.mqtt.client as mqtt
# from filllib.initerpeter import Fill_interpreter
# from filllib.smapler import Ultrasonic_Sampler
# from time import sleep

# sampler = Ultrasonic_Sampler(trig_pin=23, echo_pin=24)

# interp = Fill_interpreter(
#     empty_distance_cm=12.0,
#     full_distance_cm=3.0,
#     smoothing_window=5,
#     change_threshold_percent=5.0,
# )

# client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
# client.connect("localhost", 1883)
# client.loop_forever()
# distance = sampler.read()

# if distance is None:
#     print("Invalid reading")
# else:
#     state, event = interp.update(distance)
#     print(state)

#     if event:
#         print("EVENT:", event)

# sleep(1)

# client.publish(topic="smartbin",payload=event["fill_percent"])

# sampler.close()

import json
import sys
from time import sleep
from uuid import uuid4

import click
import paho.mqtt.client as mqtt

from filllib.smapler import Ultrasonic_Sampler
from filllib.initerpeter import Fill_interpreter
from pirlib.functions import utc_now_iso


class Data:
    def __init__(
        self,
        device_id: str,
        bin_id: str,
        state_topic: str,
        event_topic: str,
        status_topic: str,
        ha_config_topic: str,
        qos: int,
    ):
        self.device_id = device_id
        self.bin_id = bin_id
        self.state_topic = state_topic
        self.event_topic = event_topic
        self.status_topic = status_topic
        self.ha_config_topic = ha_config_topic
        self.qos = qos
        self.metrics = {
            "states_published": 0,
            "events_published": 0,
        }


def publish_ha_discovery(client, userdata: Data):
    config = {
        "name": f"{userdata.bin_id} Fill Level",
        "state_topic": userdata.state_topic,
        "value_template": "{{ value_json.fill_percent }}",
        "json_attributes_topic": userdata.state_topic,
        "unit_of_measurement": "%",
        "icon": "mdi:trash-can",
        "unique_id": f"{userdata.bin_id}_fill_level",
        "availability": {
            "topic": userdata.status_topic,
            "payload_available": "online",
            "payload_not_available": "offline",
            "value_template": "{{ value_json.status }}",
        },
        "device": {
            "identifiers": [userdata.bin_id],
            "name": f"Smart Wastebin {userdata.bin_id}",
            "model": "Smart Wastebin v1",
            "manufacturer": "ECE CK801 Team",
        },
    }

    client.publish(userdata.ha_config_topic, json.dumps(config), qos=userdata.qos, retain=True)


def on_connect(client, userdata: Data, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"[Fill Producer] Failed to connect: {reason_code}", file=sys.stderr)
        return

    print("[Fill Producer] Connected. Publishing HA discovery and online status...")
    publish_ha_discovery(client, userdata)

    client.publish(userdata.status_topic, json.dumps({"status": "online"}), qos=userdata.qos, retain=True)


def build_state_payload(
    userdata: Data,
    state: dict,
):
    return {
        "@context": "models/context.jsonld",
        "event_time": utc_now_iso(),
        "device-id": userdata.device_id,
        "bin_id": userdata.bin_id,
        "event_type": "fill_level_state",
        **state,
    }


def build_event_payload(userdata: Data, event: dict, seq: int, run_id: str):
    return {
        "@context": "models/context.jsonld",
        "madeBySensor": f"urn:dev:team-01:{userdata.device_id}",
        "WasteBin": f"urn:dev:team-01:wastebin-{userdata.bin_id.split('-')[-1]}",
        "Enviroment": "urn:env:team-01:site-01",
        "event_time": utc_now_iso(),
        "ingest_time": "",
        "device-id": userdata.device_id,
        "bin_id": userdata.bin_id,
        "event_type": "fill_level_changed",
        "seq": seq,
        "run-id": run_id,
        "pipeline_latency_ms": 0,
        **event,
    }


def ultrasonic_producer(
    userdata: Data,
    trig_pin: int,
    echo_pin: int,
    empty_distance: float,
    full_distance: float,
    sample_interval: float,
    smoothing_window: int,
    change_threshold: float,
    broker: str,
    port: int,
    duration: float,
    verbose: bool,
):
    sampler = Ultrasonic_Sampler(trig_pin=trig_pin, echo_pin=echo_pin)
    interpreter = Fill_interpreter(
        empty_distance_cm=empty_distance,
        full_distance_cm=full_distance,
        smoothing_window=smoothing_window,
        change_threshold_percent=change_threshold,
    )

    run_id = str(uuid4())
    seq = 0

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=userdata)
    client.on_connect = on_connect

    try:
        client.connect(broker,port)
        client.loop_start()

        print(
            f"[Fill Producer] device={userdata.device_id} bin={userdata.bin_id} "
            f"trig={trig_pin} echo={echo_pin} empty={empty_distance}cm full={full_distance}cm"
        )

        elapsed = 0.0

        while elapsed < duration:
            distance_cm = sampler.read()

            if distance_cm is None:
                if verbose:
                    print("[Fill Producer] Invalid distance reading")
                sleep(sample_interval)
                elapsed += sample_interval
                continue

            state, event = interpreter.update(distance_cm)

            state_payload = build_state_payload(userdata, state)

            client.publish(userdata.state_topic, json.dumps(state_payload), qos=userdata.qos, retain=True)
            userdata.metrics["states_published"] += 1

            if verbose:
                print(
                    f"[Fill Producer] distance={state['distance_cm']}cm "
                    f"fill={state['fill_percent']}% state={state['fill_state']}"
                )

            if event is not None:
                seq += 1
                event_payload = build_event_payload(userdata=userdata, event=event, seq=seq, run_id=run_id)

                client.publish(userdata.event_topic, json.dumps(event_payload), qos=userdata.qos, retain=False)
                userdata.metrics["events_published"] += 1

                if verbose:
                    print(
                        f"[Fill Producer] Event seq={seq}: "
                        f"{event_payload['fill_state']} "
                        f"({event_payload['fill_percent']}%) reason={event_payload['reason']}"
                    )

            sleep(sample_interval)
            elapsed += sample_interval

        print(f"[Fill Producer] Duration {duration}s reached. Stopping.")

    except KeyboardInterrupt:
        print("\n[Fill Producer] Ctrl-C received. Stopping.")

    except Exception as exc:
        print(f"[Fill Producer] Runtime error: {exc}", file=sys.stderr)
        raise

    finally:
        try:
            client.publish(userdata.status_topic, json.dumps({"status": "offline"}), qos=userdata.qos, retain=True)
            client.loop_stop()
            client.disconnect()
            sampler.close()
        finally:
            print(
                f"[Fill Producer] Done. "
                f"States published: {userdata.metrics['states_published']}, "
                f"Events published: {userdata.metrics['events_published']}"
            )


@click.command()
@click.option("--device-id", required=True, type=str, help="Fill sensor device ID")
@click.option("--bin-id", required=True, type=str, help="Wastebin ID, e.g. bin-01")
@click.option("--trig-pin", required=True, type=int, help="HC-SR04 trigger GPIO pin")
@click.option("--echo-pin", required=True, type=int, help="HC-SR04 echo GPIO pin")
@click.option("--empty-distance", required=True, type=float, help="Distance in cm when bin is empty")
@click.option("--full-distance", required=True, type=float, help="Distance in cm when bin is considered full")
@click.option("--sample-interval", default=5.0, type=float, help="Seconds between distance samples")
@click.option("--smoothing-window", default=5, type=int, help="Number of samples used for median smoothing")
@click.option("--change-threshold", default=5.0, type=float, help="Minimum fill percent change needed to emit event")
@click.option("--duration", default=999999.0, type=float, help="Run duration in seconds")
@click.option("--broker", required=True, type=str, default="localhost", help="MQTT broker host")
@click.option("--port", required=True, type=int, default=1883, help="MQTT broker port")
@click.option("--state-topic", default="smartbin/bin-01/fill-01/state", type=str, help="MQTT retained fill state topic")
@click.option("--event-topic", default="smartbin/bin-01/fill-01/events", type=str, help="MQTT fill event topic")
@click.option("--status-topic", default="smartbin/bin-01/fill-01/status", type=str, help="MQTT fill sensor status topic")
@click.option("--ha-config-topic", default="homeassistant/sensor/bin-01_fill_level/config", type=str, help="Home Assistant discovery topic")
@click.option("--qos", default=1, type=int, help="MQTT QoS level")
@click.option("--verbose", is_flag=True, default=False, help="Print readings and events")


def main(device_id, bin_id, trig_pin, echo_pin, empty_distance, full_distance, sample_interval, smoothing_window, 
    change_threshold, duration, broker, port, state_topic, event_topic, status_topic, ha_config_topic, qos, verbose):

    if qos not in (0, 1, 2):
        print("Error: --qos must be 0, 1, or 2", file=sys.stderr)
        raise SystemExit(2)

    if sample_interval <= 0:
        print("Error: --sample-interval must be positive", file=sys.stderr)
        raise SystemExit(2)

    if duration <= 0:
        print("Error: --duration must be positive", file=sys.stderr)
        raise SystemExit(2)

    if empty_distance <= full_distance:
        print("Error: --empty-distance must be greater than --full-distance", file=sys.stderr)
        raise SystemExit(2)

    if smoothing_window <= 0:
        print("Error: --smoothing-window must be positive", file=sys.stderr)
        raise SystemExit(2)

    userdata = Data(
        device_id=device_id,
        bin_id=bin_id,
        state_topic=state_topic,
        event_topic=event_topic,
        status_topic=status_topic,
        ha_config_topic=ha_config_topic,
        qos=qos,
    )

    ultrasonic_producer(
        userdata=userdata,
        trig_pin=trig_pin,
        echo_pin=echo_pin,
        empty_distance=empty_distance,
        full_distance=full_distance,
        sample_interval=sample_interval,
        smoothing_window=smoothing_window,
        change_threshold=change_threshold,
        broker=broker,
        port=port,
        duration=duration,
        verbose=verbose,
    )


if __name__ == "__main__":
    main()