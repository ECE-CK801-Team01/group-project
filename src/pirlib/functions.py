from datetime import datetime,timezone

def parse_iso_utc(s:str):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )