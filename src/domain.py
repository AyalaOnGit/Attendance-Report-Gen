from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class AttendanceRow:
    date: str
    day: str
    location: str
    entry: str
    exit: str
    break_minutes: Optional[str] = None
    total: Optional[str] = None
    h100: Optional[str] = None
    h125: Optional[str] = None
    h150: Optional[str] = None
    shabbat: Optional[str] = None

@dataclass
class AttendanceReport:
    rows: List[AttendanceRow] = field(default_factory=list)
    report_type: str = "TYPE_B"
    employee_name: str = ""
    summary: Dict[str, str] = field(default_factory=dict)
