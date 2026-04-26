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


### Topic Structure
 
```
smartbin/<bin-id>/<sensor-id>/events   ← motion event records
smartbin/<bin-id>/<sensor-id>/status   ← retained online/offline status
```
 
The consumer subscribes to `smartbin/+/+/events` — the `+` wildcard matches any bin and any
sensor automatically.
 
---
 
## Repository Structure
 
```
group-project/
├── README.md
├── .gitignore
├── src/                        ← all runnable code
│   ├── producer.py              ← sensor reader + MQTT publisher
│   ├── consumer.py              ← MQTT subscriber + JSONL writer
│   ├── Dockerfile               ← builds producer/consumer image
│   ├── docker-compose.yml       ← full stack: broker + producer + consumer
│   ├── mosquitto.conf           ← minimal broker configuration
│   ├── requirements.txt
│   ├── .dockerignore
│   ├── pirlib/
│   │   ├── sampler.py           ← raw GPIO read via gpiozero
│   │   ├── initerpeter.py       ← debounce + event interpretation
│   │   └── functions.py         ← shared timestamp utilities
│   └── models/
│       ├── context.jsonld       ← JSON-LD context for event records
│       ├── sensor.jsonld        ← PIR sensor semantic description
│       ├── wastebin.jsonld      ← wastebin entity description
│       └── environment.jsonld  ← deployment environment description
└── docs/
    └── ontology.md              ← custom ontology terms (team namespace)
```
 
---
 
## Hardware Requirements
 
| Component | Details |
|---|---|
| Raspberry Pi 5 | Edge device, runs all components |
| PIR Sensor HC-SR501 | Wired to GPIO pin 17 |
 
---
 
## Quick Start
 
### Option A — Docker Compose (recommended)
 
```bash
git clone <your-repo-url>
cd group-project/code
 
docker compose up --build
```
 
This starts three containers — **broker**, **producer**, and **consumer** — on a shared private network.
 
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

### Option B — Run directly on the Pi
 
**1. Install Mosquitto:**
```bash
sudo apt-get install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto && sudo systemctl start mosquitto
```
 
**2. Set up Python environment:**
```bash
cd group-project/src
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
 
**3. Start the consumer** (Terminal 1):
```bash
python3 consumer.py \
  --broker localhost \
  --port 1883 \
  --event-topic "smartbin/+/+/events" \
  --status-topic "smartbin/+/+/status" \
  --qos 1 \
  --out motion_pipeline.jsonl \
  --verbose
```
 
**4. Start the producer** (Terminal 2):
```bash
python3 producer.py \
  --device-id pir-01 \
  --pin 17 \
  --sample-interval 0.5 \
  --cooldown 2 \
  --min-high 0.3 \
  --duration 6000 \
  --broker localhost \
  --port 1883 \
  --event-topic smartbin/bin-01/pir-01/events \
  --status-topic smartbin/bin-01/pir-01/status \
  --qos 1 \
  --verbose
```
 
---
 
## Data Format
 
Each motion event is written as a single JSON-LD record on one line (JSONL):
 
```json
{
  "@context": "models/context.jsonld",
  "madeBySensor": "urn:dev:team-01:pir-01",
  "WasteBin": "urn:dev:team-01:wastebin-01",
  "Enviroment": "urn:env:team-01:site-01",
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
 
| Milestone | Lab | Description |
|---|---|---|
| M1 | Lab 01 | Project foundation — repo, structure, documentation |
| M2 | Lab 02 | PIR sensor integration — `pirlib`, JSONL event logger |
| M3 | Lab 03 | Modular pipeline — producer/consumer separation |
| M4 | Lab 04 | Containerization — Docker image and Compose stack |
| M5 | Lab 05 | JSON-LD data modeling — semantic entity descriptions |
| M6 | Lab 06 | MQTT messaging — decoupled pub/sub pipeline |
 
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
