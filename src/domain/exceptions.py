class ReportGenError(Exception):
    """Base exception for all ReportGen errors."""


class ParseError(ReportGenError):
    """Raised when OCR text cannot be parsed into a valid AttendanceReport."""


class TransformationError(ReportGenError):
    """Raised when a transformation step produces an invalid row."""


class OutputError(ReportGenError):
    """Raised when PDF or Excel export fails."""
