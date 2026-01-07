import json
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class EventType(Enum):
    MARKET_UPDATE = "MARKET_UPDATE"
    EXOGENOUS_CONTRACT = "EXOGENOUS_CONTRACT"
    NEGOTIATION_START = "NEGOTIATION_START"
    OFFER_MADE = "OFFER_MADE"
    OFFER_REJECTED = "OFFER_REJECTED"
    CONTRACT_SIGNED = "CONTRACT_SIGNED"
    PRODUCTION_RUN = "PRODUCTION_RUN"
    DAILY_SUMMARY = "DAILY_SUMMARY"


@dataclass
class Event:
    simulation_id: str
    day: int
    event_type: str
    agent_id: str
    details: dict[str, Any]
    timestamp: float = 0.0

    def to_dict(self):
        return asdict(self)


class Logger:
    def __init__(self, filename="scml_log.json"):
        self.filename = filename
        self.events: list[Event] = []
        self.simulation_id = f"sim_{int(time.time())}"

    def log(self, day: int, event_type: EventType, agent_id: str, details: dict):
        event = Event(
            simulation_id=self.simulation_id,
            day=day,
            event_type=event_type.value,
            agent_id=agent_id,
            details=details,
            timestamp=time.time(),
        )
        self.events.append(event)

    def save(self):
        with open(self.filename, "w") as f:
            json.dump([e.to_dict() for e in self.events], f, indent=2)
        print(f"Simulation data saved to {self.filename} ({len(self.events)} events)")
