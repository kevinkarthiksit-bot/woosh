from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
LEADS_FILE = BASE_DIR / "leads.json"

app = FastAPI(title="Woosh API", version="1.0.0")

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


if not LEADS_FILE.exists():
    LEADS_FILE.write_text("[]", encoding="utf-8")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def read_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/contact")
def save_contact(lead: ContactLead) -> dict[str, str]:
    try:
        current = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Leads data store is corrupted") from exc

    current.append(lead.model_dump())
    LEADS_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")

    return {"message": "Thanks! Your booking request has been received."}
