import logging
from domain.domain import AttendanceRow

logger = logging.getLogger('reportgen')


from abc import ABC, abstractmethod


class TransformationObserver(ABC):
    """Observer interface — implement to react to transformation events."""

    @abstractmethod
    def on_row_transformed(self, original: AttendanceRow, result: AttendanceRow) -> None: ...

    @abstractmethod
    def on_row_fallback(self, original: AttendanceRow, error: Exception) -> None: ...


class LoggingObserver(TransformationObserver):
    """Logs every transformation and every fallback — no coupling to the service."""

    def on_row_transformed(self, original: AttendanceRow, result: AttendanceRow) -> None:
        logger.debug(
            "transformed %s: %s→%s  %s→%s",
            original.date, original.entry, result.entry, original.exit, result.exit,
        )

    def on_row_fallback(self, original: AttendanceRow, error: Exception) -> None:
        logger.warning("fallback on %s — %s", original.date, error)


class ValidationObserver(TransformationObserver):
    """Counts successes and failures; exposes them for testing or monitoring."""

    def __init__(self) -> None:
        self.successes = 0
        self.failures = 0

    def on_row_transformed(self, original: AttendanceRow, result: AttendanceRow) -> None:
        self.successes += 1

    def on_row_fallback(self, original: AttendanceRow, error: Exception) -> None:
        self.failures += 1
