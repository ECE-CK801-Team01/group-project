import click
import paho.mqtt.client as mqtt
from pirlib.functions import utc_now_iso

class Data():
    def __init__(self,  omni_topic:str, qos:int, out:str):
        self.omni_topic = omni_topic
        self.qos = qos
        self.out = out
        
def on_connect(client, userdata:Data, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"[Consumer] Failed to connect: {reason_code}. Retrying connection")
    else:
        print(f"[Consumer] Connected. Subscribing...")
        client.subscribe(userdata.omni_topic)
        print(f"[Consumer] Subscribed to '{userdata.omni_topic}' ")

def on_message(client, userdata:Data, message):
    message_list = message.topic.split("/")
    _, bin_num , sensor_num , event_type = message_list
    output = f"Bin:{bin_num} sensor:{sensor_num} time:{utc_now_iso()} event_type:{event_type} \n"
    print(output)
    with open(userdata.out,"a") as f:
        f.write(output)
        f.flush()

@click.command()
@click.option("--broker", required=True, type=str, default="localhost", help="The broker to be used")
@click.option("--port", required=True, type=int, default=1883, help="The device port")
@click.option("--qos", required=True, type=int, default=1, help="Client QoS level")
@click.option("--out", required=True, type=str, help="Output file name")

def main(broker, port, qos, out):
    omni_topic = "smartbin/+/+/#"
    userdata = Data(omni_topic=omni_topic,qos=qos,out=out)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,userdata=userdata)
    client.on_message = on_message
    client.on_connect = on_connect
    client.connect(host=broker,port=port)


    try:
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()

if __name__ == "__main__":
    main()
