from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
LEADS_FILE = BASE_DIR / "leads.json"
SETTINGS_FILE = BASE_DIR / "slot_settings.json"
DB_LOCK = Lock()

DEFAULT_TIMES = ["09:00", "11:00", "13:00", "15:00", "17:00"]
DEFAULT_CAPACITY = 4

app = FastAPI(title="Woosh API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ContactLead(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(min_length=7, max_length=20)
    vehicle: str = Field(pattern=r"^(Car|Bike|Deep Cleaning)$")
    booking_date: str
    time_slot: str

    @field_validator("booking_date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
        if parsed < date.today():
            raise ValueError("Past dates are not allowed")
        return value

    @field_validator("time_slot")
    @classmethod
    def validate_time_slot(cls, value: str) -> str:
        if value not in DEFAULT_TIMES:
            raise ValueError("Invalid time slot")
        return value


class SlotSettings(BaseModel):
    default_capacity: int = Field(default=DEFAULT_CAPACITY, ge=1, le=50)
    blocked_dates: list[str] = Field(default_factory=list)
    custom_slot_capacity: dict[str, dict[str, int]] = Field(default_factory=dict)


if not LEADS_FILE.exists():
    LEADS_FILE.write_text("[]", encoding="utf-8")

if not SETTINGS_FILE.exists():
    SETTINGS_FILE.write_text(
        json.dumps(
            {
                "default_capacity": DEFAULT_CAPACITY,
                "blocked_dates": [],
                "custom_slot_capacity": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Corrupted data in {path.name}") from exc


def _read_settings() -> SlotSettings:
    raw = _read_json(SETTINGS_FILE, {})
    return SlotSettings.model_validate(raw)


def _bookings_for(date_value: str, time_slot: str, bookings: list[dict[str, Any]]) -> int:
    return len(
        [
            b
            for b in bookings
            if b.get("booking_date") == date_value
            and b.get("time_slot") == time_slot
            and b.get("status", "confirmed") != "rejected"
        ]
    )


def _resolve_capacity(settings: SlotSettings, date_value: str, time_slot: str) -> int:
    per_date = settings.custom_slot_capacity.get(date_value, {})
    return int(per_date.get(time_slot, settings.default_capacity))


@app.get("/")
def read_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/booking/availability")
def booking_availability(date_value: str) -> dict[str, Any]:
    settings = _read_settings()
    selected = datetime.strptime(date_value, "%Y-%m-%d").date()
    if selected < date.today():
        return {"date": date_value, "blocked": True, "slots": []}

    is_blocked = date_value in settings.blocked_dates
    bookings = _read_json(LEADS_FILE, [])

    slots = []
    for slot in DEFAULT_TIMES:
        capacity = _resolve_capacity(settings, date_value, slot)
        booked = _bookings_for(date_value, slot, bookings)
        slots.append(
            {
                "time": slot,
                "capacity": capacity,
                "booked": booked,
                "remaining": max(capacity - booked, 0),
                "isAvailable": (not is_blocked) and booked < capacity,
            }
        )

    return {"date": date_value, "blocked": is_blocked, "slots": slots}


@app.get("/api/booking/settings")
def booking_settings() -> dict[str, Any]:
    settings = _read_settings()
    return settings.model_dump()


@app.post("/contact")
def save_contact(lead: ContactLead) -> dict[str, str]:
    with DB_LOCK:
        settings = _read_settings()
        if lead.booking_date in settings.blocked_dates:
            raise HTTPException(status_code=400, detail="Selected date is blocked")

        current = _read_json(LEADS_FILE, [])
        capacity = _resolve_capacity(settings, lead.booking_date, lead.time_slot)
        booked = _bookings_for(lead.booking_date, lead.time_slot, current)

        if booked >= capacity:
            raise HTTPException(status_code=409, detail="Selected slot is full")

        booking_data = lead.model_dump()
        booking_data["created_at"] = datetime.utcnow().isoformat() + "Z"
        booking_data["status"] = "pending"
        current.append(booking_data)
        LEADS_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")

    return {"message": "Thanks! Your booking has been confirmed.", "bookingStatus": "pending"}
