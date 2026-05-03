import datetime
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class AttendanceRow:
    date: datetime.date
    day: str
    location: str
    entry: datetime.time
    exit: datetime.time
    break_minutes: int = 30
    total: Optional[float] = None
    h100: Optional[float] = None
    h125: Optional[float] = None
    h150: Optional[float] = None
    shabbat: Optional[float] = None

    def __post_init__(self) -> None:
        if self.exit <= self.entry:
            raise ValueError(f"exit {self.exit} must be after entry {self.entry}")


@dataclass(frozen=True)
class AttendanceReport:
    rows: Tuple[AttendanceRow, ...] = field(default_factory=tuple)
    report_type: str = 'TYPE_B'
    employee_name: str = ''
    summary: Dict[str, str] = field(default_factory=dict)
