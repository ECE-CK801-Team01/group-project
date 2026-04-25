# ΟΜΑΔΑ 1 #

## ΜΕΛΗ ## 
<ul>
 <li>ΔΡΑΚΟΣ ΕΜΜΑΝΟΥΗΛ-ΔΡΑΚΟΣ</li>
 <li>ΖΙΑΚΑΣ ΝΙΚΟΛΑΟΣ</li>
 <li>ΣΑΜΑΡΑΣ ΘΕΟΦΑΝΗΣ</li>
</ul>

# Smart Wastebin — Team 01

A smart waste bin system built on a Raspberry Pi 5 using a PIR motion 
sensor to detect deposits, process events through an MQTT pipeline, 
and log structured data for monitoring and analysis.

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
