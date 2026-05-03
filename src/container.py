"""
Composition Root — the single place where all dependencies are wired together.
main.py calls build_container() and receives ready-to-use service objects.
No other module knows about concrete implementations.
"""
from application.parsers import TypeAParser, TypeBParser, BaseParser
from application.transformation import (
    TransformationService,
    TypeATransformationStrategy,
    TypeBTransformationStrategy,
    ValidatingStrategyDecorator,
    BaseTransformationStrategy,
)
from application.observers import LoggingObserver, ValidationObserver
from application.classifier import identify_report_type
from infrastructure.ocr_engine import get_pdf_text_and_layout
from infrastructure.exporters import export_results

# ─── Registry: הוספת TYPE_C = שורה אחת כאן בלבד ───
_PARSER_REGISTRY: dict[str, type[BaseParser]] = {
    'TYPE_A': TypeAParser,
    'TYPE_B': TypeBParser,
}

_STRATEGY_REGISTRY: dict[str, BaseTransformationStrategy] = {
    'TYPE_A': ValidatingStrategyDecorator(TypeATransformationStrategy()),
    'TYPE_B': ValidatingStrategyDecorator(TypeBTransformationStrategy()),
}


class Container:
    """Holds all wired service instances."""

    def __init__(self) -> None:
        self._validation_observer = ValidationObserver()

        self.transformation_service = TransformationService(
            strategy_registry=_STRATEGY_REGISTRY,
            observers=[LoggingObserver(), self._validation_observer],
        )
        self.identify_report_type = identify_report_type
        self.get_pdf_text_and_layout = get_pdf_text_and_layout
        self.export_results = export_results

    def create_parser(self, report_type: str, text: str, layout=None) -> BaseParser:
        parser_class = _PARSER_REGISTRY.get(report_type, TypeBParser)
        return parser_class(text, layout)

    @property
    def validation_observer(self) -> ValidationObserver:
        return self._validation_observer


def build_container() -> Container:
    return Container()
