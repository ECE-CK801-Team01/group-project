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
│   │   ├── __init__.py
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
