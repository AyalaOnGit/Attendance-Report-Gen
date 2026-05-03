from application.parsers import TypeAParser, TypeBParser, BaseParser


def create_parser(report_type: str, text: str, layout=None) -> BaseParser:
    """Returns the correct parser. Registry lives in container.py."""
    raise NotImplementedError("create_parser must be injected via Container")
