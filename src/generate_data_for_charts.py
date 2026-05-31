import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

DAYS = 30
OUT_PATH = "data/demo_events.jsonl"
BINS = [
    {
        "bin_id": "bin-01",
        "sensor_id": "pir-01",
        "name": "Cafeteria",
        "rate_fn": "cafeteria",
        "latency_mean": 200,   # Pi over WiFi
        "latency_std": 50,
    },
    {
        "bin_id": "bin-02",
        "sensor_id": "pir-02",
        "name": "Hallway",
        "rate_fn": "hallway",
        "latency_mean": 350,   # edge device over WiFi
        "latency_std": 80,
    },
    {
        "bin_id": "bin-03",
        "sensor_id": "pir-03",
        "name": "Lab Room",
        "rate_fn": "lab_room",
        "latency_mean": 350,   # same edge laptop as bin-02
        "latency_std": 80,
    },
]


def rate_cafeteria(day_of_week, hour):
    """Strong midday peaks, quieter on weekends but not silent"""
    weekend = day_of_week >= 5
    base = 1
    if 8 <= hour <= 9: base = 12  
    if 12 <= hour <= 14: base = 30     
    if 18 <= hour <= 19: base = 18     
    if 0 <= hour <= 6: base = 0      
    return base * (0.4 if weekend else 1.0)


def rate_hallway(day_of_week, hour):
    """Steady business-hour traffic, reduced on weekends"""
    weekend = day_of_week >= 5
    if 7 <= hour <= 19: base = 15
    elif 20 <= hour <= 22: base = 5
    else: base = 1
    return base * (0.3 if weekend else 1.0)


def rate_lab_room(day_of_week, hour):
    """Afternoon-heavy weekday traffic, near-zero on weekends"""
    weekend = day_of_week >= 5
    if weekend:return 1
    if 10 <= hour <= 11: return 6      
    if 13 <= hour <= 17:  return 20     
    if 18 <= hour <= 20: return 8      
    return 1


RATE_FNS = {"cafeteria": rate_cafeteria, "hallway": rate_hallway,"lab_room": rate_lab_room}

def latency_ms(mean, std):
    """Gaussian latency with few spikes (1% chance of 5-10x normal)"""
    base = max(0.0, random.gauss(mean, std))
    if random.random() < 0.01:
        base *= random.uniform(5, 10)
    return base

def iso(dt):
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def generate(days, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    run_ids = {b["bin_id"]: str(uuid4()) for b in BINS}
    seqs = {b["bin_id"]: 0 for b in BINS}

    records = []

    start_day = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) - timedelta(days=days - 1)

    for d in range(days):
        day = start_day + timedelta(days=d)
        for hour in range(24):
            for b in BINS:
                rate = RATE_FNS[b["rate_fn"]](day.weekday(), hour)
                count = max(0, int(random.gauss(rate, rate * 0.3)))
                for _ in range(count):
                    seqs[b["bin_id"]] += 1
                    event_dt = day.replace(hour=hour) + timedelta(
                        minutes=random.randint(0, 59),
                        seconds=random.randint(0, 59),
                        milliseconds=random.randint(0, 999),
                    )
                    lat = latency_ms(b["latency_mean"], b["latency_std"])
                    ingest_dt = event_dt + timedelta(milliseconds=lat)

                    record = {
                        "@context": "models/context.jsonld",
                        "madeBySensor": f"urn:dev:team-01:{b['sensor_id']}",
                        "WasteBin": f"urn:dev:team-01:{b['bin_id'].replace('bin', 'wastebin')}",
                        "Enviroment": "urn:env:team-01:site-01",
                        "event_time": iso(event_dt),
                        "ingest_time": iso(ingest_dt),
                        "device-id": b["sensor_id"],
                        "event_type": "motion",
                        "motion_state": "detected",
                        "seq": seqs[b["bin_id"]],
                        "run-id": run_ids[b["bin_id"]],
                        "pipeline_latency_ms": round(lat, 1),
                        "synthetic": True,
                    }
                    records.append((event_dt, record))

    records.sort(key=lambda r: r[0])

    with open(out_path, "w", encoding="utf-8") as f:
        for _, record in records:
            f.write(json.dumps(record) + "\n")

    return len(records)


if __name__ == "__main__":
    days = DAYS
    if len(sys.argv) > 1: days = int(sys.argv[1])

    out = OUT_PATH
    if len(sys.argv) > 2: out = sys.argv[2]

    n = generate(days, out)
    print(f"Generated {n} synthetic events over {days} days "
          f"across {len(BINS)} bins -> {out}")