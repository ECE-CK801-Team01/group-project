import paho.mqtt.client as mqtt
import json
import joblib
import click
import time
import numpy as np
from datetime import datetime
from pirlib.functions import utc_now_iso

def load_model(path: str):
    return joblib.load(path)

def predict_next_hour(model):
    now = datetime.now()
    next_hour = (now.hour + 1) % 24
    day_of_week = now.weekday()
    is_weekend = 1 if day_of_week >= 5 else 0

    features = [[day_of_week, next_hour, is_weekend]]

    prediction = model.predict(features)[0]
    probabilities = model.predict_proba(features)[0]
    class_index = list(model.classes_).index(prediction)
    confidence = round(probabilities[class_index], 3)

    return prediction,confidence,next_hour

def publish_discovery(client, publish_topic, bin_id):
    """Register the ML prediction sensor with Home Assistant via MQTT Discovery."""
    config = {
        "name": f"{bin_id} Busy Prediction",
        "state_topic": publish_topic,
        "value_template": "{{ value_json.prediction }}",
        "icon": "mdi:chart-bell-curve-cumulative",
        "unique_id": f"{bin_id}_busy_prediction",
        "json_attributes_topic": publish_topic,
        "device": {
            "identifiers": [bin_id],
            "name": f"Smart Wastebin {bin_id}",
            "model": "Smart Wastebin v1",
            "manufacturer": "ECE CK801 Team"
        }
    }
    client.publish(f"homeassistant/sensor/{bin_id}_busy_prediction/config",json.dumps(config), retain=True, qos=1)
    print("[ML Sensor] HA discovery published.")


@click.command()
@click.option("--broker", default="localhost", help="MQTT broker hostname or IP")
@click.option("--port", default=1883, type=int, help="MQTT broker port")
@click.option("--publish-topic", default="smartbin/bin-01/prediction", help="Topic to publish predictions to")
@click.option("--model-path", default="models/busy_predictor.joblib", help="Path to trained model file")
@click.option("--interval", default=60, type=int, help="Seconds between predictions")
@click.option("--bin-id", default="bin-01", help="Bin identifier")

def main(broker, port, publish_topic, model_path, interval, bin_id):
    model = load_model(model_path)
    print(f"[ML Sensor] Model loaded from {model_path}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="virtual-sensor-ml")
    client.connect(broker, port)
    client.loop_start()
    publish_discovery(client, publish_topic, bin_id)
    print(f"[ML Sensor] Publishing to '{publish_topic}' every {interval}s")

    try:
        while True:
            prediction, confidence, next_hour = predict_next_hour(model)

            payload = {
                "prediction": prediction,
                "confidence": confidence,
                "predicted_hour": next_hour,
                "timestamp": utc_now_iso(),
                "model": "busy_predictor",
                "features": {
                    "day_of_week": datetime.now().weekday(),
                    "hour": next_hour,
                    "is_weekend": 1 if datetime.now().weekday() >= 5 else 0,
                }
            }

            client.publish(publish_topic, json.dumps(payload), qos=1,retain=True)
            print(f"[ML Sensor] Hour {next_hour:02d}:00 → {prediction} (confidence: {confidence*100:.1f}%)")
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[ML Sensor] Shutting down.")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()