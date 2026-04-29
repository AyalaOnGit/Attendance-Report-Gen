from parsers import TypeAParser, TypeBParser

PARSER_REGISTRY = {
    "TYPE_A": TypeAParser,
    "TYPE_B": TypeBParser,
}


def create_parser(report_type, text, layout=None):
    parser_class = PARSER_REGISTRY.get(report_type, TypeBParser)
    return parser_class(text, layout)

