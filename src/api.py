from flask import Flask,request
from flask_restx import Api,Resource,reqparse,fields
from pirlib.functions import utc_now_iso,parse_iso_utc
import json,os
import paho.mqtt.client as mqtt
import threading

data_dir = "/data"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR,"models")

def get_data_dir():
    """Return the data directory to use, preferring /data when available."""
    if os.path.isdir(data_dir):
        return data_dir
    local_data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(local_data_dir, exist_ok=True)
    return local_data_dir

EVENTS_FILE = os.path.join(get_data_dir(), "motion_events.jsonl")

def shorten_id(full_id):
    """Shorten full URN ID to simple name like pir-01 or bin-01."""
    last_part = full_id.split(":")[-1]
    if "wastebin" in last_part:
        return last_part.replace("wastebin", "bin")
    return last_part

def find_bin(bin_id):
    """Find a bin by short ID from wastebin.jsonld."""
    bins_data = load_JSON("./models/wastebin.jsonld")
    for item in bins_data.get("@graph", []):
        if shorten_id(item.get("@id")) == bin_id:
            return {
                "id": shorten_id(item.get("@id")),
                "name": item.get("rdfs:label", "Unknown Bin"),
                "location": "site-01",  # Inferred from models
                "status": "active"
            }
    return None

def get_sensor_by_id(sensor_id):
    """Find a sensor by short ID from sensor.jsonld."""
    all_sensors = registered_sensor()
    index = int(sensor_id.split("-")[-1])
    output =  all_sensors["sensors"]
    return output[index-1]

def registered_sensor():
    """Return all registered sensors from sensor.jsonld."""
    sensors_data = load_JSON(os.path.join(MODELS_DIR,"sensor.jsonld"))
    # bins_data = load_JSON("./models/wastebin.jsonld")
    data = []
    sensors = []
    graph = sensors_data["@graph"]
    for node in graph:
        node_type = node.get("@type",[])

        if isinstance(node_type,list) and "sosa:Sensor" in node_type:
            data.append(node)

        for info in data:
            sensor_id = info["@id"]
            sensor_id = sensor_id.split(":")[-1]
            model = info["rdfs:label"]
            sensor_model,sensor_type = model.split(" ")
            mounted_on = sensor_id.split("-")[-1]
            output = {
                "id": sensor_id,
                "type": sensor_type,
                "model": sensor_model,
                "mounted_on": f"wastebin-{mounted_on}",
                "status": "active"
            }
            if output not in sensors:
                sensors.append(output)
    return {"sensors": sensors}

def get_sensor_for_bin(bin_id):
    """Get the sensor ID hosted by the bin from wastebin.jsonld."""
    bins_data = load_JSON("./models/wastebin.jsonld")
    for item in bins_data.get("@graph", []):
        if shorten_id(item.get("@id")) == bin_id:
            hosted = item.get("sosa:hosts")
            if hosted:
                return shorten_id(hosted.get("@id"))
    return None

def load_JSON(filepath):
    with open(file=filepath,mode="r") as f:
        output = json.load(f)
        return output
    
def save_record(record:dict):
    record_file = os.path.join(get_data_dir(), "record.jsonl")
    os.makedirs(os.path.dirname(record_file), exist_ok=True)
    with open(record_file, "a") as f:
        f.write(json.dumps(record) + "\n")
        f.flush()

def load_events(filepath,limit=None,sensor_id=None):
    events = []

    if not os.path.isfile(filepath):
        return events
    
    with open(file=filepath,mode="r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            made_by = record.get("madeBySensor") or record.get("device-id")
            if sensor_id and made_by:
                if sensor_id != shorten_id(made_by):
                    continue

            events.append(record)

        events.reverse()

        if limit:
            events = events[:limit]
        
        return events
   
events_parser = reqparse.RequestParser()
events_parser.add_argument("limit", type=int, default=50, help="Max events to return")
events_parser.add_argument("start", type=str, help="Start datetime (ISO format)")
events_parser.add_argument("end", type=str, help="End datetime (ISO format)")

app = Flask(__name__)
api = Api(
    app=app,
    version="1.0",
    title="Smart Wastebin API",
    description="REST API for querying Smart Wastebin sensor data and bin status"
)

# bin_model = api.model(name = "Bin", model = load_JSON("./labs/lab08/models/wastebin_ver2.jsonld"))
# event_model = api.model(name = "Event", model = load_JSON("./labs/lab08/models/context.jsonld"))

bin_model = api.model("Bin", {
    "id": fields.String(required=True, description="Bin unique identifier"),
    "name": fields.String(description="Human-readable name"),
    "location": fields.String(description="Deployment location"),
    "status": fields.String(description="Current status"),
})

event_model = api.model("Event", {
    "resultTime": fields.String(description="ISO timestamp of the event"),
    "madeBySensor": fields.String(description="Sensor ID that produced this event"),
    "hasSimpleResult": fields.String(description="Motion state (detected/clear)"),
    "pipeline_latency_ms": fields.Float(description="Pipeline latency in ms"),
})

emptied_model = api.model("EmptiedRecord",{
    "bin_id":fields.String(description="Bin Identifier"),
    "emptied_at":fields.String(description="ISO timestamp of when the bin was emptied"),
    "emptied_by":fields.String(description="Who emptied the bin")
})

sensor_model = api.model("Sensor",{
    "id" : fields.String(description="Sensor unique indentifier"),
    "type" : fields.String(description="Sensor type (PIR, ultrasonic, etc.)"),
    "model" : fields.String(description="Hardware model"),
    "mounted_on" : fields.String(description="Bin this sensor is mounted on"),
    "status" : fields.String(description="Current sensor status")

})
sensors_ns = api.namespace("sensors",description = "Sensor operations")
ns = api.namespace("bins",description="Wastebin operations")

@ns.route("/")
class BinList(Resource):
    def get(self):
        """List all registered bins."""
        bins_data = load_JSON("./models/wastebin.jsonld")
        bins = []
        for item in bins_data.get("@graph", []):
            if "s4evi:Container" in item.get("@type", []):
                bins.append({
                    "id": shorten_id(item.get("@id")),
                    "name": item.get("rdfs:label", "Unknown Bin"),
                    "location": "site-01",
                    "status": "active"
                })
        return {"bins": bins}, 200
    
@ns.route("/<string:bin_id>")
@ns.param("bin_id", "The bin identifier")
@ns.response(404, "Bin not found")
class Bin(Resource):
    @ns.marshal_with(bin_model)
    def get(self, bin_id):
        """Get details for a specific bin."""
        bin_data = find_bin(bin_id)
        if not bin_data:
            api.abort(404, f"Bin {bin_id} not found")
        return bin_data


@ns.route("/<string:bin_id>/events")
@ns.param("bin_id", "The bin identifier")
class BinEvents(Resource):
    @ns.expect(events_parser)
    @ns.marshal_list_with(event_model)
    def get(self, bin_id):
        """Get motion events for a specific bin."""
        args = events_parser.parse_args()
        events = load_events(
            EVENTS_FILE,
            limit=args["limit"],
            sensor_id=get_sensor_for_bin(bin_id),
        )
        return events
    
@ns.route("/<string:bin_id>/emptied")
@ns.param("bin_id","The bin identifier")
class BinEmptied(Resource):
    @ns.expect(emptied_model)
    @ns.response(201,"Bin marked as emptied")
    @ns.response(404,"Bin not found")
    def post(self,bin_id):
        bin_data = find_bin(bin_id=bin_id)

        if not bin_data:
            ns.abort(404, f"Bin {bin_data} not found")

        data = request.get_json() or {}

        record = {
            "bin_id" : bin_id,
            "emptied_at" : data["emptied_at"] or utc_now_iso(),
            "emptied_by" : data["emptied_by"] or "unknown"
        }

        save_record(record=record)

        return record, 201

@sensors_ns.route("/")
class SensorList(Resource):
    @sensors_ns.marshal_list_with(sensor_model)
    def get(self):
        all_registered_sensors = registered_sensor()
        return all_registered_sensors["sensors"]

@sensors_ns.route("/<sensor_id>")
@sensors_ns.param("sensor_id","The sensor identifier")
@sensors_ns.response(404,"Sensor not found")
class Sensor(Resource):

    @sensors_ns.marshal_with(sensor_model)
    def get(self,sensor_id):
        sensor = get_sensor_by_id(sensor_id=sensor_id)
        if not sensor:
            sensors_ns.abort(404,f"Sensor {sensor_id} not found")
        
        return sensor

wastebin_api = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,clean_session=False,client_id="My API")
topic_store = {}
topic_lock = threading.Lock()

def on_message(client,userdata,msg):
    # save_record(msg.payload.decode())

    with topic_lock:

        topic_store[msg.topic] = {
            "topic" : msg.topic,
            "payload" : msg.payload.decode("utf-8"),
            "qos" : msg.qos,
            "retain" : msg.retain,
            "timestamp" : utc_now_iso()
        }

wastebin_api.on_message = on_message

broker_host = os.environ.get("MQTT_BROKER", "localhost")
broker_port = int(os.environ.get("MQTT_PORT", "1883"))
try:
    wastebin_api.connect(broker_host, port=broker_port, keepalive=60)
    wastebin_api.subscribe("smartbin/#", qos=1)
    wastebin_api.loop_start()
    print(f"[API] Connected to MQTT broker at {broker_host}:{broker_port}")
except Exception as e:
    print(f"[API] No broker available at {broker_host}:{broker_port}: {e} — MQTT endpoints disabled")

mqtt_ns = api.namespace("mqtt",description = "MQTT broker interaction")

publish_model = api.model("MQTTPublish",{
    "topic" : fields.String(description="MQTT topic to publish to"),
    "payload" : fields.String(description="Message payload"),
    "qos" : fields.Integer(description="Quality of Service (0, 1 or 2)"),
    "retain" : fields.Boolean(default = False,description = "Retain this message on the broker")
})

@mqtt_ns.route("/publish")
class MQTTPublish(Resource):
    @mqtt_ns.expect(publish_model)
    @mqtt_ns.response(200,"Message published")
    @mqtt_ns.response(400,"Invalid request")

    def post(self):
        wastebin_api.publish("/","hello")
        data = request.get_json() or {}
        response = {
            "topic" : data["topic"],
            "payload" : data["payload"],
            "qos" : data["qos"],
            "retain" : data["retain"]
        }

        if not (response["topic"] or response["payload"]):
            mqtt_ns.abort(400,"Both 'topic' and 'payload' are required")

        if not (response["qos"] in [0,1,2]):
            mqtt_ns.abort(400,"QoS must be 0, 1 or 2")

        result = wastebin_api.publish(response["topic"],response["payload"],qos = response["qos"],retain = response["retain"])

        return {
            "status":"published",
            "topic":response["topic"],
            "payload":response["payload"],
            "qos" : response["qos"],
            "retain" : response["retain"],
            "mqtt_rc" : result.rc
            },200
@mqtt_ns.route("/topics")
class MQTTTopics(Resource):
    def get(self):
        with topic_lock:

            response = {
                "topic_count" : len(topic_store),
                "topics" : list(topic_store.values())
            }
        
        return response,200

@mqtt_ns.route("/topics/<topic>")
@mqtt_ns.param("topic","MQTT topic path, for example smartbin/bin-01/pir-01/motion")
class MQTTTopicDetail(Resource):
    @mqtt_ns.response(404,"Topic not found or no message received yet")
    def get(self,topic):

        with topic_lock:
            if topic not in topic_store:
                mqtt_ns.abort(404,f"No message received on {topic}")

            return topic_store[topic], 200
        
@mqtt_ns.route("/<bin_id>/emptied")
@mqtt_ns.param("bin_id","The bin identifier")
class BinEmptied(Resource):
    @mqtt_ns.expect(emptied_model)
    @mqtt_ns.response(201,"Bin marked as emptied")
    @mqtt_ns.response(400,"Bin not found")
    def post(bin_id):

        bin_data = find_bin(bin_id=bin_id)
        if not bin_data:
            mqtt_ns.abort(400,f"Bin {bin_id} not found")

        data = request.get_json()
        record = {
            "bin_id" : bin_id,
            "emptied_at" : data["emptied_at"] or utc_now_iso(),
            "emptied_by" : data["emptied_by"] or "unknown"
        }
        save_record(record=record)

        wastebin_api.publish(f"smartbin/{bin_id}/status",json.dumps({"state":"emptied","emptied_at":record["emptied_at"]}),qos=1,retain=True)

        return record,201
    
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0",port=5000)