# Smart Wastebin — Team 01

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%205-red)
![Broker](https://img.shields.io/badge/Broker-Mosquitto%20MQTT-purple)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![License](https://img.shields.io/badge/License-MIT-green)

A smart waste bin system built on a Raspberry Pi 5 using a PIR motion 
sensor to detect deposits, process events through an MQTT pipeline, 
and log structured data for monitoring and analysis.

Built as part of ECE CK801

## Team
- ΔΡΑΚΟΣ ΕΜΜΑΝΟΥΗΛ-ΔΡΑΚΟΣ
- ΖΙΑΚΑΣ ΝΙΚΟΛΑΟΣ
- ΣΑΜΑΡΑΣ ΘΕΟΦΑΝΗΣ

## System Overview
The system consists of:
- A PIR sensor (HC-SR501) connected to the Pi's GPIO pins
- A producer that reads the sensor and publishes motion events via MQTT
- A Mosquitto broker that routes messages between components
- A consumer that receives events, enriches them, and writes JSONL logs
- Docker Compose for portable, reproducible deployment
- Home Assistant for creating a GUI
- An API to make requests/changes to the system without direct access
- A ML algorithm that makes prediction based on previous similar events

### Topic Structure
 
```
smartbin/<bin-id>/<sensor-id>/events   ← motion event records
smartbin/<bin-id>/<sensor-id>/status   ← retained online/offline status
```
 
The consumer subscribes to `smartbin/+/+/events` — the `+` wildcard matches any bin and any
sensor automatically.
 
---
 
## Repository Structure
 
``` bash
group-project/
├── .gitignore
├── README.md
├── docs/
│   └── ontology.md
└── src/ #all runnable code
    ├── .dockerignore
    ├── .env
    ├── Dockerfile #builds the image of each component
    ├── analyze.py
    ├── api.py #Open and Async API calls for the system 
    ├── asyncapi.yaml #Description of the developed API
    ├── consumer.py #Receives events, records them in files and sends appropriate HA messages 
    ├── docker-compose-real.edge.yml #Runs on the edge device and sends interpreted PIR events
    ├── docker-compose.central.yml #Runs on the main computer and receives the produced events
    ├── docker-compose.edge.yml #Runs on a secondary computer to create mock events for testing
    ├── docker-compose.yml
    ├── filllib/ #Reading the Ultrasonic input 
    │   ├── initerpeter.py #Event interpretation
    │   ├── smapler.py #raw GPIO read via gpiozero for PIR sensor
    │   └── test_fill.py
    ├── flows.json #Node-Red flows 
    ├── generate_data_for_charts.py
    ├── models/
    │   ├── busy_predictor.joblib
    │   ├── context.jsonld #JSON-LD context for event records
    │   ├── environment.jsonld #deployment environment description 
    │   ├── sensor.jsonld #PIR and Ultrasonic sensors semantic description
    │   └── wastebin.jsonld #wastebins entity description
    ├── mosquitto.conf #minimal broker configuration
    ├── pirlib/ #Reading the PIR input
    │   ├── functions.py
    │   ├── initerpeter.py #debounce + event interpretation
    │   ├── sampler.py #raw GPIO read via gpiozero for PIR sensor
    │   └── sim_sampler.py #simulated sensor data 
    ├── producer.py #Motion sensor producer, sends the events through MQTT
    ├── requirements.txt
    ├── train_model.py
    ├── ultrasonic_producer.py #Ultrasonic sensor, sends the events through MQTT
    ├── virtual_sensor_combiner.py 
    ├── virtual_sensor_ml.py
    └── virtual_sensor_rules.py
```
 
---
 
## Hardware Requirements
 
| Component | Details |
|---|---|
| Raspberry Pi 5 | Edge device, runs all components |
| PIR Sensor HC-SR501 | Wired to GPIO pin 17 |
| Ultrasonic Sensor HC-SR04 | Wired to pin 23/24
 
---
 
## Quick Start
 
### Option A — Docker Compose (recommended)
 
```bash
git clone <your-repo-url>
cd group-project/src
```
 
We have configured our system to run on at least two devices,ideally three, connected to the same network, so we suggest cloning the repo to all of them if you are planning to use them

We also recommend changing the `.env` variables to match your system

On the edge device with the sensor connected you run:

``` bash
docker compose -f docker-compose-real.edge.yml up -d --build
```
This builds the image and runs the edge script detached

On the main system that will work as the "server" which receives all messages made run:

``` bash
docker compose -f docker-compose.central.yml up -d --build
```

This not only runs the receiver but set's up everything else we have created for the project 

In case you don't have an edge device or the necessary sensor you can run mock events with:

```bash
docker compose -f docker-compose.edge.yml up -d --build
```



To run without GPIO hardware (no PIR sensor connected):
```bash
docker compose up broker consumer
```
 
View live output:
```bash
docker compose logs -f consumer
docker compose logs -f producer
```
 
Stop everything:
```bash
docker compose down
```
 
Stop and delete saved data:
```bash
docker compose down -v
```
---
 
## Data Format
 
Each motion event is written as a single JSON-LD record on one line (JSONL):
 
```json
{
  "@context": "models/context.jsonld",
  "madeBySensor": "urn:dev:team-01:pir-01",
  "WasteBin": "urn:dev:team-01:wastebin-01",
  "Environment": "urn:env:team-01:site-01",
  "event_time": "2026-04-25T10:15:30.123Z",
  "ingest_time": "2026-04-25T10:15:30.125Z",
  "device-id": "pir-01",
  "event_type": "motion",
  "motion_state": "detected",
  "seq": 1,
  "run-id": "abc123...",
  "pipeline_latency_ms": 2.1
}
```
 
Records use the [SOSA/SSN](https://www.w3.org/TR/vocab-ssn/) ontology for semantic interoperability.
Custom ontology terms are defined in [`docs/ontology.md`](docs/ontology.md).
 
---
 
## Milestones
### Lab milestones 
| Milestone | Lab | Description |
|---|---|---|
| M1 | Lab 01 | Project foundation — repo, structure, documentation |
| M2 | Lab 02 | PIR sensor integration — `pirlib`, JSONL event logger |
| M3 | Lab 03 | Modular pipeline — producer/consumer separation |
| M4 | Lab 04 | Containerization — Docker image and Compose stack |
| M5 | Lab 05 | JSON-LD data modeling — semantic entity descriptions |
| M6 | Lab 06 | MQTT messaging — decoupled pub/sub pipeline |
| M7 | Lab 07 | Integrated Home Assistant for visualization of the sensor output |
| M8 | Lab 08| Created an API for interaction with the system |
| M9 | Lab 09| Build virtual sensors and make ML predictions for the wastebin usage | 
| M10 | Lab 10| Added Node-Red as a low code platform for easy visualizations |
| M11 | Lab 11| Updated the Home Assistant dashboard and created charts for data visualization |

### Beyond the labs
To improve the functions of our system, we fully detached the three parts of our system, creating a separate docker-compose for each of them, and made them communicate through the network making it so they don't have to run on the same device anymore. We also experimented with an ultrasonic sensor to post the fill lever of the wastebin  
## MIT License

Copyright (c) 2026 Team 01 — Δράκος Εμμανουήλ-Δράκος, Ζιάκας Νικόλαος, Σαμαράς Θεοφάνης

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
