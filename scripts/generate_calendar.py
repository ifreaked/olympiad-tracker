"""Generate a deterministic all-day iCalendar feed from the source JSON."""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "physics_olympiads.json"
OUTPUT = ROOT / "docs" / "olympiads.ics"


def escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line: str) -> list[str]:
    encoded = line.encode("utf-8")
    chunks = []
    limit = 75
    while encoded:
        cut = min(limit, len(encoded))
        while cut < len(encoded) and cut > 0 and (encoded[cut] & 0xC0) == 0x80:
            cut -= 1
        if not cut:
            raise ValueError("Unable to fold UTF-8 line")
        chunks.append(encoded[:cut].decode("utf-8"))
        encoded = encoded[cut:]
        limit = 74
    return chunks if len(chunks) == 1 else [chunks[0]] + [" " + part for part in chunks[1:]]


def uid(olympiad_id: str, event: dict) -> str:
    key = json.dumps([olympiad_id, event], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24] + "@olympiad-tracker"


def event_lines(olympiad: dict, event: dict) -> list[str]:
    start_value = event["date"] if "date" in event else event["start"]
    end_value = event["date"] if "date" in event else event["end"]
    start = date.fromisoformat(start_value)
    end = date.fromisoformat(end_value)
    end_exclusive = end + timedelta(days=1)
    summary = event.get("summary")
    if summary is None:
        summary = f"{olympiad['name']} | {event['title']}"
    description_lines = []
    if olympiad.get("level"):
        description_lines.append(f"Уровень: {olympiad['level']}")
    if olympiad.get("classes"):
        description_lines.append(f"Классы: {olympiad['classes']}")
    if olympiad.get("url"):
        description_lines.append(f"Сайт: {olympiad['url']}")
    if event.get("note"):
        description_lines.append(event["note"])
    description_lines.extend(event.get("description", []))
    description = "\n".join(description_lines)
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid(olympiad['id'], event)}",
        f"DTSTAMP:20260101T000000Z",
        f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{end_exclusive.strftime('%Y%m%d')}",
        f"SUMMARY:{escape(summary)}",
    ]
    if description_lines:
        lines.append(f"DESCRIPTION:{escape(description)}")
    if olympiad.get("url"):
        lines.append(f"URL:{escape(olympiad['url'])}")
    lines.extend(["CATEGORIES:Физика\\, олимпиада", "END:VEVENT"])
    return lines


def generate() -> str:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    lines = [
        "BEGIN:VCALENDAR",
        "PRODID:-//ifreaked//Physics Olympiads//RU",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape(data['calendar']['name'])}",
        "X-WR-TIMEZONE:Europe/Moscow",
    ]
    for olympiad in data["olympiads"]:
        for event in olympiad["events"]:
            lines.extend(event_lines(olympiad, event))
    lines.append("END:VCALENDAR")
    return "\r\n".join(line for item in lines for line in fold(item)) + "\r\n"


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generate(), encoding="utf-8", newline="")
