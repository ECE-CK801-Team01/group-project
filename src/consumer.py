import paho.mqtt.client as mqtt
import json
from pirlib.functions import utc_now_iso,parse_iso_utc
import click
import sys 

class Data():
    def __init__(self, event_topic:str, status_topic:str, qos:int, out_motion:str, out_fill:str, verbose:bool):
        self.event_topic = event_topic
        self.status_topic = status_topic
        self.qos = qos
        self.out_motion = out_motion
        self.out_fill = out_fill
        self.verbose = verbose
        self.metrics = {"total_receive": 0, "total_latency": 0.0, "average_latency": 0.0}

def on_message(client, userdata:Data, message):
    message_last_topic = message.topic.split("/")[-1]
    sensor_type = message.topic.split("/")[-2]
    sensor_type = sensor_type.split("-")[0]

    try:
        parsed_input = json.loads(message.payload.decode())
    except json.JSONDecodeError as e:
        print(f"[Consumer] Could not parse message on {message.topic}: {e}", file=sys.stderr)
        return
    
    if message_last_topic == "events":
        ingest_time = utc_now_iso()
        pipeline_latency = parse_iso_utc(ingest_time)-parse_iso_utc(parsed_input["event_time"])
        parsed_input["ingest_time"] = ingest_time
        parsed_input["pipeline_latency_ms"] = pipeline_latency.total_seconds()*1000
        
        userdata.metrics["total_receive"]  += 1
        userdata.metrics["total_latency"]  += parsed_input["pipeline_latency_ms"]
        userdata.metrics["average_latency"] = (userdata.metrics["total_latency"] / userdata.metrics["total_receive"])

        if sensor_type == "pir":
            with open(userdata.out_motion, "a") as f:
                f.write(json.dumps(parsed_input) + "\n")
                f.flush()
        
        if sensor_type == "ultra":
            with open(userdata.out_fill, "a") as f:
                f.write(json.dumps(parsed_input) + "\n")
                f.flush()
        
        if userdata.verbose:
            print(f"[Consumer] seq={parsed_input.get('seq')} "
                  f"latency={parsed_input['pipeline_latency_ms']:.1f}ms "
                  f"avg={userdata.metrics['average_latency']:.1f}ms "
                  f"total={userdata.metrics['total_receive']}")

    elif message_last_topic == "status":
        print(f"[Consumer] Status update on {message.topic}: {parsed_input}")

def on_connect(client, userdata:Data, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"[Consumer] Failed to connect: {reason_code}. Retrying connection")
    else:
        print(f"[Consumer] Connected. Subscribing...")
        client.subscribe([
            (userdata.event_topic, userdata.qos),
            (userdata.status_topic, userdata.qos),
        ])
        print(f"[Consumer] Subscribed to '{userdata.event_topic}' "
              f"and '{userdata.status_topic}' (QoS={userdata.qos})")
        print(f"[Consumer] Writing motion events to '{userdata.out_motion}' and fill events to '{userdata.out_fill}' — press Ctrl-C to stop.")

@click.command()
@click.option("--broker", required=True, type=str, default="localhost", help="The broker to be used")
@click.option("--port", required=True, type=int, default=1883, help="The device port")
@click.option("--event-topic", required=True, type=str, default="smartbin/+/+/events", help="The client's event topic")
@click.option("--status-topic", required=True, type=str, default="smartbin/+/+/status", show_default=True, help="The client's status topic")
@click.option("--qos", required=True, type=int, default=1, help="Client QoS level")
@click.option("--out_motion", required=True, type=str, help="Motion output file name")
@click.option("--out_fill", required=True, type=str, help="Fill output file name")
@click.option("--verbose", is_flag=True, default=False, help="Print each received event to the terminal")

def main(broker, port, event_topic, status_topic, qos, out_motion, out_fill, verbose):
    if qos not in (0, 1, 2):
        print("Error: --qos must be 0, 1, or 2", file=sys.stderr)
        raise SystemExit(2)
    
    userdata = Data(event_topic=event_topic, status_topic=status_topic, qos=qos, out_motion=out_motion, out_fill=out_fill, verbose=verbose)
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host=broker, port=port)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\n[Consumer] Shutting down. "
            f"Total received: {userdata.metrics['total_receive']}, "
            f"avg latency: {userdata.metrics['average_latency']:.1f}ms")
        client.disconnect()


if __name__ == "__main__":
    main()