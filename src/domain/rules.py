import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class TransformationRules:
    offset_modulus: int
    standard_day_hours: float
    break_minutes: int


@dataclass(frozen=True)
class ParserRules:
    min_entry: datetime.time
    max_entry: datetime.time
    min_exit: datetime.time
    max_exit: datetime.time
    min_shift_minutes: int
    max_shift_minutes: int
    break_minutes: int


TYPE_A_TRANSFORM = TransformationRules(
    offset_modulus=11,
    standard_day_hours=8.0,
    break_minutes=30,
)

TYPE_B_TRANSFORM = TransformationRules(
    offset_modulus=11,
    standard_day_hours=8.0,
    break_minutes=30,
)

PARSER_RULES = ParserRules(
    min_entry=datetime.time(5, 0),
    max_entry=datetime.time(13, 0),
    min_exit=datetime.time(10, 0),
    max_exit=datetime.time(23, 59),
    min_shift_minutes=60,
    max_shift_minutes=14 * 60,
    break_minutes=30,
)
