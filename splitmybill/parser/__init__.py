from __future__ import annotations

from enum import Enum
from pathlib import Path

from splitmybill.parser.base import BillParserBase
from splitmybill.parser.instacart import InstacartParser
from splitmybill.parser.llm import AnthropicParser

__all__ = [
    "AnthropicParser",
    "BillParserBase",
    "InstacartParser"
]


class ParserType(str, Enum):
    INSTACART = "instacart"
    ANTHROPIC = "anthropic"


def determine_parser(receipt_path: Path | str) -> ParserType:
    if isinstance(receipt_path, str):
        receipt_path = Path(receipt_path)
    if receipt_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
        return ParserType.ANTHROPIC
    elif receipt_path.suffix.lower() == ".html":
        if InstacartParser.is_valid_html(receipt_path.read_text()):
            return ParserType.INSTACART
        else:
            msg = ("HTML file is not a recognized Instacart receipt. "
                   "Maybe the layout has changed?")
            raise ValueError(msg)
    else:
        msg = (f"Unsupported file type: {receipt_path.suffix}")
        raise ValueError(msg)


def get_parser(
        parser_type: ParserType,
        bill_path: Path | str,
        **kwargs
    ) -> BillParserBase:
    if isinstance(bill_path, str):
        bill_path = Path(bill_path)

    if parser_type == ParserType.INSTACART:
        return InstacartParser(bill_path.read_text(), **kwargs)
    elif parser_type == ParserType.ANTHROPIC:
        return AnthropicParser(bill_path, **kwargs)
    else:
        msg = f"Unknown parser type: {parser_type}"
        raise ValueError(msg)
