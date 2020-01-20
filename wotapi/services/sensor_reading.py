from dataclasses import dataclass, asdict, field
import json
import time


@dataclass
class SensorReading:
    values: dict = field(default_factory=dict)
    timestamp: int = int(time.time())

    def to_json(self):
        return json.dumps(asdict(self))
