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
