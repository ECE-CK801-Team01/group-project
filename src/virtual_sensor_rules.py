import paho.mqtt.client as mqtt
import json,click
from time import sleep
from collections import deque
from datetime import timedelta
from threading import Lock
from pirlib.functions import utc_now_iso,parse_iso_utc

event_times = deque()
event_lock = Lock()

def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode().strip())
        if payload.get("motion_state") == "detected":
            with event_lock:
                event_times.append(utc_now_iso())
    except Exception as e:
        print(f"Couldn't load the message: {e}")

def evaluate_usage(window_minutes = 10):
    cutoff_time = parse_iso_utc(utc_now_iso())-timedelta(minutes=window_minutes)

    with event_lock:
        while event_times and parse_iso_utc(event_times[0]) < cutoff_time:
            event_times.popleft()

        count = len(event_times)
    if count == 0:
        return "idle",count
    elif count <= 5:
        return "low",count
    elif count<=15:
        return "medium",count
    else:
        return "high",count

def publish_discovery(client, publish_topic):
    """Register the usage intensity sensor with Home Assistant via MQTT Discovery."""
    config = {
        "name": "Bin Usage Intensity",
        "state_topic": publish_topic,
        "value_template":"{{ value_json.usage_level }}",
        "icon": "mdi:trash-can",
        "unique_id": "wastebin_01_usage",
        "json_attributes_topic": publish_topic,
        "device": {
            "identifiers": ["bin-01"],
            "name": "Smart Wastebin 01",
            "model": "Smart Wastebin v1",
            "manufacturer":"ECE CK801 Team"
        }
    }
    client.publish("homeassistant/sensor/wastebin_01_usage/config",json.dumps(config),retain=True,qos=1)
    print("[Rules Sensor] HA discovery published.")

@click.command()
@click.option("--broker",required = True, type = str, default = "localhost", help= "The broker to be used")
@click.option("--port",required = True, type = int, default = 1883, help= "The device port")
@click.option("--subscribe-topic",required = True, type = str, default = "smartbin/bin-01/pir-01/events", help= "The client's event topic")
@click.option("--publish-topic",required = True, type = str, default = "smartbin/bin-01/usage", help= "The client's status topic")
@click.option("--window",required = True,type = int,default = 10,help = "Usage evaluation window in minutes")
@click.option("--interval" , required = True,type = int,default = 30,help = "Time between evaluations in seconds")

def main(broker,port,subscribe_topic,publish_topic,window,interval):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id="Virtual-sensor-rules")
    client.on_message = on_message
    client.connect(host=broker,port=port)
    client.loop_start()
    client.subscribe(topic=subscribe_topic, qos=1)
    publish_discovery(client, publish_topic)
    print(subscribe_topic,window,interval)

    try:
        while True:
            usage_level,event_count = evaluate_usage(window_minutes=window)
            payload = json.dumps({
                "usage_level" : usage_level,
                "event_count" : event_count,
                "window_size" : window,
                "current_time" : utc_now_iso() 
            })

            client.publish(topic=publish_topic,payload=payload,qos=1,retain=True)
            print(usage_level)
            sleep(interval)

    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()
        print("User terminated with [Ctrl-C]")

if __name__ == "__main__":
    main()