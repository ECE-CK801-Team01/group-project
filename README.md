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
