import paho.mqtt.client as mqtt
from pirlib.functions import utc_now_iso, parse_iso_utc
import json, sys, os, click
from datetime import datetime, timezone
from collections import deque

# ── Terminal helpers ──────────────────────────────────────────────────────────

CLEAR    = "\033[2J\033[H"
BOLD     = "\033[1m"
RESET    = "\033[0m"
CYAN     = "\033[96m"
GREEN    = "\033[92m"
YELLOW   = "\033[93m"
RED      = "\033[91m"
MUTED    = "\033[90m"
WHITE    = "\033[97m"
BG_DARK  = "\033[48;5;234m"

W = 70  # dashboard width

def bar(value, max_value, width=30, fill="█", empty="░"):
    filled = int((value / max_value) * width) if max_value > 0 else 0
    filled = min(filled, width)
    return GREEN + fill * filled + MUTED + empty * (width - filled) + RESET

def hline(char="─"):
    return MUTED + char * W + RESET

def header(title):
    pad = (W - len(title) - 2) // 2
    return CYAN + BOLD + "┌" + "─" * (W-2) + "┐\n" + \
           "│" + " " * pad + title + " " * (W - 2 - pad - len(title)) + "│\n" + \
           "└" + "─" * (W-2) + "┘" + RESET

def row(label, value, color=WHITE):
    label_str = f"  {label:<22}"
    return MUTED + label_str + RESET + color + BOLD + str(value) + RESET

# ── Shared state ──────────────────────────────────────────────────────────────

class Data:
    def __init__(self, topic: str, status_topic: str, qos: int, history: int):
        self.topic        = topic
        self.status_topic = status_topic
        self.qos          = qos
        self.device_status = "unknown"
        self.device_id     = "—"
        self.run_id        = "—"

        # counters
        self.total         = 0
        self.latencies     = deque(maxlen=history)  # last N latencies
        self.events_log    = deque(maxlen=8)         # last 8 events for feed

        # session tracking
        self.session_start = None
        self.last_event    = None
        self.min_latency   = float("inf")
        self.max_latency   = float("-inf")

# ── Dashboard renderer ────────────────────────────────────────────────────────

def render(data: Data):
    avg_lat = (sum(data.latencies) / len(data.latencies)) if data.latencies else 0.0
    last_lat = data.latencies[-1] if data.latencies else 0.0

    uptime = "—"
    if data.session_start:
        elapsed = (datetime.now(timezone.utc) - data.session_start).total_seconds()
        h, m, s = int(elapsed // 3600), int((elapsed % 3600) // 60), int(elapsed % 60)
        uptime = f"{h:02d}:{m:02d}:{s:02d}"

    last_event_str = "—"
    if data.last_event:
        diff = (datetime.now(timezone.utc) - data.last_event).total_seconds()
        last_event_str = f"{diff:.1f}s ago"

    # status colour
    status_color = GREEN if data.device_status == "online" \
                   else RED if data.device_status == "offline" \
                   else YELLOW

    lines = []
    lines.append(CLEAR)
    lines.append(header("  🗑️  SMART WASTEBIN  —  LIVE DASHBOARD  "))
    lines.append("")

    # Device status block
    lines.append(CYAN + BOLD + "  DEVICE" + RESET)
    lines.append(hline())
    lines.append(row("Device ID",     data.device_id))
    lines.append(row("Status",        data.device_status.upper(), status_color))
    lines.append(row("Run ID",        data.run_id[:36] if data.run_id != "—" else "—", MUTED))
    lines.append(row("Session uptime", uptime))
    lines.append(row("Last event",    last_event_str))
    lines.append("")

    # Event counters
    lines.append(CYAN + BOLD + "  EVENTS" + RESET)
    lines.append(hline())
    lines.append(row("Total received", f"{data.total}"))
    lines.append(f"  {'Motion bar':<22}{bar(min(data.total, 50), 50)}")
    lines.append("")

    # Latency
    lines.append(CYAN + BOLD + "  PIPELINE LATENCY" + RESET)
    lines.append(hline())
    lines.append(row("Last",    f"{last_lat:.2f} ms"))
    lines.append(row("Average", f"{avg_lat:.2f} ms"))
    lines.append(row("Min",     f"{data.min_latency:.2f} ms" if data.min_latency != float('inf') else "—"))
    lines.append(row("Max",     f"{data.max_latency:.2f} ms" if data.max_latency != float('-inf') else "—"))
    lat_scale = max(data.max_latency, 10) if data.max_latency != float("-inf") else 10
    lines.append(f"  {'Latency bar':<22}{bar(last_lat, lat_scale, fill='▓', empty='░')}")
    lines.append("")

    # Recent events feed
    lines.append(CYAN + BOLD + "  RECENT EVENTS" + RESET)
    lines.append(hline())
    if data.events_log:
        for entry in reversed(data.events_log):
            lines.append(f"  {MUTED}{entry}{RESET}")
    else:
        lines.append(f"  {MUTED}Waiting for events...{RESET}")
    lines.append("")
    lines.append(hline())
    lines.append(f"  {MUTED}Subscribed to: {data.topic}   |   Press Ctrl-C to exit{RESET}")

    print("\n".join(lines), flush=True)

# ── Callbacks ─────────────────────────────────────────────────────────────────

def on_connect(client, userdata: Data, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"[Dashboard] Failed to connect: {reason_code}")
    else:
        client.subscribe([
            (userdata.topic, userdata.qos),
            (userdata.status_topic, userdata.qos),
        ])
        userdata.session_start = datetime.now(timezone.utc)
        render(userdata)


def on_message(client, userdata: Data, message):
    last_segment = message.topic.split("/")[-1]

    try:
        payload = json.loads(message.payload.decode())
    except json.JSONDecodeError:
        return

    if last_segment == "events":
        ingest_time = utc_now_iso()
        latency_ms  = (
            parse_iso_utc(ingest_time) - parse_iso_utc(payload["event_time"])
        ).total_seconds() * 1000

        userdata.total += 1
        userdata.latencies.append(latency_ms)
        userdata.last_event = datetime.now(timezone.utc)
        userdata.device_id  = payload.get("device-id", userdata.device_id)
        userdata.run_id     = payload.get("run-id", userdata.run_id)

        if latency_ms < userdata.min_latency:
            userdata.min_latency = latency_ms
        if latency_ms > userdata.max_latency:
            userdata.max_latency = latency_ms

        seq = payload.get("seq", "?")
        t   = payload.get("event_time", "")[-12:-1]  # just the time part
        userdata.events_log.append(
            f"seq={seq:<4}  {t}  latency={latency_ms:.1f}ms"
        )

    elif last_segment == "status":
        userdata.device_status = payload.get("status", "unknown")

    render(userdata)


# ── CLI ───────────────────────────────────────────────────────────────────────

@click.command()
@click.option("--broker",       required=True, type=str, default="localhost", show_default=True,
              help="MQTT broker hostname or IP")
@click.option("--port",         required=True, type=int, default=1883, show_default=True,
              help="MQTT broker port")
@click.option("--topic",        required=True, type=str,
              default="smartbin/+/+/events", show_default=True,
              help="Topic to subscribe to for events")
@click.option("--status-topic", required=True, type=str,
              default="smartbin/+/+/status", show_default=True,
              help="Topic to subscribe to for device status")
@click.option("--qos",          required=True, type=int, default=1, show_default=True,
              help="QoS level (0, 1, or 2)")
@click.option("--history",      type=int, default=20, show_default=True,
              help="Number of recent latency samples to track")
def main(broker, port, topic, status_topic, qos, history):
    if qos not in (0, 1, 2):
        print("Error: --qos must be 0, 1, or 2", file=sys.stderr)
        raise SystemExit(2)

    userdata = Data(topic=topic, status_topic=status_topic, qos=qos, history=history)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host=broker, port=port)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\n[Dashboard] Shutting down. Total events seen: {userdata.total}")
        client.disconnect()


if __name__ == "__main__":
    main()