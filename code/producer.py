import paho.mqtt.client as mqtt
from pirlib.initerpeter import PirInterpreter
from pirlib.sampler import PirSampler
from pirlib.functions import utc_now_iso
from time import time,sleep
from uuid import uuid4
import click,json,sys

class Data():
    def __init__(self, event_topic:str, status_topic:str, qos:int):
        self.event_topic = event_topic
        self.status_topic = status_topic
        self.qos = qos
        self.metrics = {"produced": 0, "acknowledged": 0}
        self.event_mids = set()


def on_connect(client, userdata:Data, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"[Producer] Failled to connect: {reason_code}. Retrying connection")
    else:
        print(f"[Producer] connected. Setting status to online...")
        client.publish(userdata.status_topic, json.dumps({"status": "online"}),retain=True,qos = userdata.qos)

def on_publish(client, userdata, m_id, reason_code, properties):
    if reason_code.is_failure:
        print(f"[Producer] Broker rejected message (mid={m_id}): {reason_code}",
              file=sys.stderr)
    elif m_id in userdata.event_mids:
        print(f"Publishing message : {m_id} success")
        userdata.event_mids.remove(m_id)
        userdata.metrics["acknowledged"] += 1

def producer(device_id:str,
             sampler:PirSampler,
             sample_interval:float,
             interp:PirInterpreter,
             broker:str, 
             port:int, 
             duration: float,
             verbose: bool,                                
             userdata: Data,
             ) -> None:
    
    run_id = str(uuid4())
    seq = 0
    start_time = time()

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=userdata)
        client.on_connect = on_connect
        client.on_publish = on_publish
        client.connect(broker, port)
        client.loop_start()

        while time() - start_time < duration:
            cur_time = time()
            last_sample = sampler.read()
            for ev in interp.update(last_sample, cur_time):
                seq += 1
                record = {
                            "@context" : "models/context.jsonld",
                            "madeBySensor" : "urn:dev:team-01:pir-01",
                            "WasteBin" : "urn:dev:team-01:wastebin-01",
                            "Enviroment" : "urn:env:team-01:site-01",
                            "event_time" : utc_now_iso(),
                            "ingest_time" : "",
                            "device-id" : device_id,
                            "event_type" : "motion",
                            "motion_state" : "detected",
                            "seq" : seq,
                            "run-id" : run_id,
                            "pipeline_latency_ms" : 0
                            }
                if verbose:              
                    print(f"[Producer] Publishing seq={seq} at {record['event_time']}")
                info = client.publish(userdata.event_topic, json.dumps(record), userdata.qos)
                userdata.event_mids.add(info.mid)
                userdata.metrics["produced"] += 1
            sleep(sample_interval)
 
        print(f"[Producer] Duration ({duration}s) reached — stopping.")
 
    except KeyboardInterrupt:
        print("\n[Producer] Keyboard interrupt — shutting down.")

    except Exception as e:
        print(f"Error with connection and/or publishing: {e}")

    finally:
        client.publish(
            userdata.status_topic,
            json.dumps({"status": "offline"}),
            retain=True,
            qos=userdata.qos,
        )
        client.loop_stop()
        client.disconnect()
        print(
            f"[Producer] Done. "
            f"Produced: {userdata.metrics['produced']}, "
            f"Acknowledged by broker: {userdata.metrics['acknowledged']}"
        )

@click.command()
@click.option("--device-id",required = True, type = str, help= "The id of the device")
@click.option("--pin",required = True, type = int, help = "The pin to be used for the sensor outputs")
@click.option("--sample-interval", type = float,default= 5, help = "Time between measurments")
@click.option("--cooldown", type = float,default=3.0, help = "Senson's debounce time")
@click.option("--min-high", type = float, default=0.2, help = "Minimun acceptable sensor value")
@click.option("--duration", type = float,default = 30.0, help = "Duration of the session")
@click.option("--verbose", is_flag = True, default = False, help = "whether or not to print output in the terminal")
# mqtts options
@click.option("--broker",required = True, type = str, default = "localhost", help= "The broker to be used")
@click.option("--port",required = True, type = int, default = 1883, help= "The device port")
@click.option("--event-topic",required = True, type = str, default = "smartbin/+/+/events", help= "The client's event topic")
@click.option("--status-topic",required = True, type = str, default = "smartbin/+/+/status", help= "The client's status topic")
@click.option("--qos",required = True, type = int, default = 1, help= "Client QoS level")


def main(device_id,pin,sample_interval,cooldown,min_high,duration,verbose,
         broker, port, event_topic, status_topic, qos):
    
    sampler = PirSampler(pin)
    interp = PirInterpreter(cooldown_s=cooldown,min_high_s=min_high)
    userdata = Data(event_topic=event_topic, status_topic=status_topic, qos=qos)

    float_inputs = {"sample_interval":sample_interval,
                    "cooldown":cooldown,
                    "min_high":min_high,
                    "duration":duration}

    for key,value in float_inputs.items():
        if value < 0:
            print(f"{key} must be a positive number",file=sys.stderr)
            raise SystemExit(2)
        
    if qos not in (0, 1, 2):
        print("Error: --qos must be 0, 1, or 2", file=sys.stderr)
        raise SystemExit(2)
    
    try:
        producer(device_id,sampler,sample_interval,interp,
             broker, port, duration, verbose, userdata)
    except KeyboardInterrupt:
        print("Program terminated [Producer]")


if __name__ == "__main__" :
    main()

         