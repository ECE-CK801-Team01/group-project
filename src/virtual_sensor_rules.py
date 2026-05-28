import paho.mqtt.client as mqtt
import json,click
from time import sleep
from collections import deque
from datetime import timedelta
from threading import Lock
from pirlib.functions import utc_now_iso,parse_iso_utc

bin_events = {}       # Instead of one global deque, we keep a dict of deques keyed by bin_id and
known_bins = {}       # each bin gets its own rolling window of event timestamps
registered = set()   
state_lock = Lock()

def parse_topic(topic):
    parts = topic.split("/")
    if len(parts) == 4 and parts[0] == "smartbin" and parts[3] == "events":
        return parts[1], parts[2]
    return None, None

def on_message(client, userdata, message):
    bin_id, sensor_id = parse_topic(message.topic)
    if bin_id is None:
        return
    payload = json.loads(message.payload.decode().strip())
    if payload.get("motion_state") == "detected":
        with state_lock:
            if bin_id not in bin_events:   
                bin_events[bin_id] = deque()
                known_bins[bin_id] = sensor_id      # The sensor doesnt have to know in advance which bins exist.
            bin_events[bin_id].append(utc_now_iso())

def evaluate_usage(bin_id, window_minutes):
    cutoff_time = parse_iso_utc(utc_now_iso())-timedelta(minutes=window_minutes)

    with state_lock:
        dq = bin_events.get(bin_id)
        if dq is None:
            return "idle", 0
        while dq and parse_iso_utc(dq[0]) < cutoff_time:
            dq.popleft()
        count = len(dq)

    if count == 0:
        return "idle",count
    elif count <= 5:
        return "low",count
    elif count<=15:
        return "medium",count
    else:
        return "high",count

def publish_discovery(client, bin_id):
    """Register the usage intensity sensor with Home Assistant via MQTT Discovery."""
    publish_topic = f"smartbin/{bin_id}/usage"
    config = {
        "name": "Bin Usage Intensity",
        "state_topic": publish_topic,
        "value_template": "{{ value_json.usage_level }}",
        "icon": "mdi:trash-can",
        "unique_id": f"{bin_id}_usage",
        "json_attributes_topic": publish_topic,
        "device": {
            "identifiers": [bin_id],
            "name": f"Smart Wastebin {bin_id}",
            "model": "Smart Wastebin v1",
            "manufacturer": "ECE CK801 Team",
        },
    }
    client.publish(
        f"homeassistant/sensor/{bin_id}_usage/config",
        json.dumps(config),
        retain=True,
        qos=1,
    )
    print(f"[Rules Sensor] HA discovery published for {bin_id}.")

@click.command()
@click.option("--broker",required = True, type = str, default = "localhost", help= "The broker to be used")
@click.option("--port",required = True, type = int, default = 1883, help= "The device port")
@click.option("--subscribe-topic",required = True, type = str, default = "smartbin/+/+/events", help= "Wildcard event topic across all bins")
@click.option("--window",required = True,type = int,default = 10,help = "Usage evaluation window in minutes")
@click.option("--interval" , required = True,type = int,default = 30,help = "Time between evaluations in seconds")

def main(broker,port,subscribe_topic,window,interval):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id="Virtual-sensor-rules")
    client.on_message = on_message
    client.connect(host=broker,port=port)
    client.loop_start()
    client.subscribe(topic=subscribe_topic, qos=1)
    print(subscribe_topic,window,interval)

    try:
        while True:
            with state_lock:
                bins_now = list(known_bins.keys())

            for bin_id in bins_now:
                if bin_id not in registered:
                    publish_discovery(client, bin_id)
                    registered.add(bin_id)

                usage_level,event_count = evaluate_usage(bin_id, window_minutes=window)
                payload = json.dumps({
                    "usage_level": usage_level,
                    "event_count": event_count,
                    "window_size": window,
                    "bin_id": bin_id,
                    "current_time": utc_now_iso(),
                })
                client.publish(topic=f"smartbin/{bin_id}/usage", payload=payload, qos=1, retain=True)
                print(f"[Rules Sensor] {bin_id}: {usage_level} ({event_count} events)")
            sleep(interval)

    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()
        print("User terminated with [Ctrl-C]")

if __name__ == "__main__":
    main()
