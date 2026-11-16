"""Database tables (owner: Member 2)."""
from datetime import datetime
from typing import Literal, Optional

from sqlmodel import Field, SQLModel

DataSource = Literal["simulated", "manual", "device"]


class Astronaut(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    mission: str
    environment: str  # "station" | "lunar_base" | "mars_transit" ...
    mission_day: int = 1


class Device(SQLModel, table=True):
    """A measuring device paired with one astronaut. Every device in this demo is SIMULATED."""
    id: Optional[int] = Field(default=None, primary_key=True)
    astronaut_id: int = Field(foreign_key="astronaut.id", index=True)
    kind: str  # key from config/devices.json
    name: str  # must say "(simulated)" for simulated devices
    token: str  # random secret sent by the device in X-Device-Token; never returned by the API
    simulated: bool = True
    last_seen: Optional[datetime] = None  # UTC


class Measurement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    astronaut_id: int = Field(foreign_key="astronaut.id", index=True)
    indicator: str = Field(index=True)  # key from config/indicators.json
    value: float
    timestamp: datetime = Field(index=True)
    # Every row says where it comes from: "simulated" (generator), "manual" (form) or "device".
    source: str = "manual"
    device_id: Optional[int] = Field(default=None, foreign_key="device.id", index=True)


class MeasurementRead(SQLModel):
    """Measurement as returned by the API, with the name of the device that sent it (if any)."""
    id: int
    astronaut_id: int
    indicator: str
    value: float
    timestamp: datetime
    source: str
    device_id: Optional[int] = None
    device_name: Optional[str] = None


class ReadingIn(SQLModel):
    indicator: str
    value: float
    timestamp: Optional[datetime] = None


class ReadingsIn(SQLModel):
    readings: list[ReadingIn] = Field(min_length=1, max_length=100)


class MeasurementCreate(SQLModel):
    indicator: str
    value: float
    timestamp: Optional[datetime] = None


class AutonomyAction(SQLModel, table=True):
    """An onboard step checked off during Earth-independent mode (one row per checked step)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    astronaut_id: int = Field(foreign_key="astronaut.id", index=True)
    indicator: str
    step_index: int
    timestamp: datetime = Field(index=True)


class ReportTransmission(SQLModel, table=True):
    """When a crew health report was sent to Earth."""
    id: Optional[int] = Field(default=None, primary_key=True)
    astronaut_id: int = Field(foreign_key="astronaut.id", index=True)
    sent_at: datetime = Field(index=True)


class ReportStep(SQLModel, table=True):
    """Snapshot of an onboard step included in a report at the moment it was sent."""
    id: Optional[int] = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="reporttransmission.id", index=True)
    indicator: str
    step_index: int
    checked_at: datetime
