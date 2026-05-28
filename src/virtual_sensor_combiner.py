import paho.mqtt.client as mqtt
import json, click
from time import sleep
from threading import Lock
from pirlib.functions import utc_now_iso

CONFIDENCE_THRESHOLD = 0.65

latest_usage = {}        # bin_id -> usage_level string
latest_prediction = {"prediction": None, "confidence": 0.0}  # system-wide
known_bins = set()
registered = set()
state_lock = Lock()

ACTIVE_USAGE = ("medium", "high")


def parse_topic(topic):
    parts = topic.split("/")
    if len(parts) == 3 and parts[0] == "smartbin" and parts[2] == "usage":
        return "usage", parts[1]
    if len(parts) == 3 and parts[0] == "smartbin" and parts[2] == "prediction":
        return "prediction", parts[1]
    return None, None


def on_message(client, userdata, message):
    try:
        kind, bin_id = parse_topic(message.topic)
        if kind is None:
            return
        payload = json.loads(message.payload.decode().strip())
        with state_lock:
            if kind == "usage":
                latest_usage[bin_id] = payload.get("usage_level", "idle")
                known_bins.add(bin_id)
            elif kind == "prediction":
                latest_prediction["prediction"] = payload.get("prediction")
                latest_prediction["confidence"] = float(payload.get("confidence", 0.0))
    except Exception as e:
        print(f"[Combiner] Couldn't process message: {e}")


def fuse(usage_level, prediction, confidence):
    active = usage_level in ACTIVE_USAGE
    trusted = (prediction is not None) and (confidence >= CONFIDENCE_THRESHOLD)

    if not trusted:
        if active:
            return "Heads-up", "Activity present — monitor"
        return "OK", "No action needed"

    if prediction == "busy" and active:
        return "Urgent", "Service soon — busy now and predicted"
    if prediction == "busy" and not active:
        return "Heads-up", "Quiet now, busy expected — be ready"
    if prediction == "quiet" and active:
        return "Unexpected", "Activity higher than forecast — check"
    return "OK", "No action needed"


def publish_discovery(client, bin_id):
    publish_topic = f"smartbin/{bin_id}/recommendation"
    config = {
        "name": "Service Recommendation",
        "state_topic": publish_topic,
        "value_template": "{{ value_json.status }}",
        "icon": "mdi:clipboard-check",
        "unique_id": f"{bin_id}_recommendation",
        "json_attributes_topic": publish_topic,
        "device": {
            "identifiers": [bin_id],
            "name": f"Smart Wastebin {bin_id}",
            "model": "Smart Wastebin v1",
            "manufacturer": "ECE CK801 Team",
        },
    }
    client.publish(
        f"homeassistant/sensor/{bin_id}_recommendation/config",
        json.dumps(config),
        retain=True,
        qos=1,
    )
    print(f"[Combiner] HA discovery published for {bin_id}.")


@click.command()
@click.option("--broker", default="localhost", help="MQTT broker hostname or IP")
@click.option("--port", default=1883, type=int, help="MQTT broker port")
@click.option("--interval", default=20, type=int, help="Seconds between recommendation updates")
def main(broker, port, interval):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="virtual-sensor-combiner")
    client.on_message = on_message
    client.connect(broker, port)
    client.loop_start()
    client.subscribe("smartbin/+/usage", qos=1)
    client.subscribe("smartbin/+/prediction", qos=1)
    print(f"[Combiner] Subscribed to usage + prediction topics. Interval={interval}s")

    try:
        while True:
            with state_lock:
                bins_now = list(known_bins)
                pred = latest_prediction["prediction"]
                conf = latest_prediction["confidence"]
                usages = dict(latest_usage)

            for bin_id in bins_now:
                if bin_id not in registered:
                    publish_discovery(client, bin_id)
                    registered.add(bin_id)

                usage_level = usages.get(bin_id, "idle")
                status, action = fuse(usage_level, pred, conf)

                payload = json.dumps({
                    "status": status,
                    "action": action,
                    "usage_level": usage_level,
                    "prediction": pred,
                    "confidence": conf,
                    "bin_id": bin_id,
                    "current_time": utc_now_iso(),
                })
                client.publish(f"smartbin/{bin_id}/recommendation", payload, qos=1, retain=True)
                print(f"[Combiner] {bin_id}: {status} — {action} (usage={usage_level}, pred={pred}@{conf})")

            sleep(interval)

    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()
        print("User terminated with [Ctrl-C]")


if __name__ == "__main__":
    main()
