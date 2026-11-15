"""Database tables (owner: Member 2)."""
from datetime import datetime
from typing import Literal, Optional

from sqlmodel import Field, SQLModel

DataSource = Literal["simulated", "manual"]


class Astronaut(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    mission: str
    environment: str  # "station" | "lunar_base" | "mars_transit" ...
    mission_day: int = 1


class Measurement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    astronaut_id: int = Field(foreign_key="astronaut.id", index=True)
    indicator: str = Field(index=True)  # key from config/indicators.json
    value: float
    timestamp: datetime = Field(index=True)
    # Every row says whether it is simulated or entered by a person.
    source: str = "manual"


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
