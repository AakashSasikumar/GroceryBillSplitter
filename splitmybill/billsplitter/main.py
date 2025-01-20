from __future__ import annotations

from typing import TYPE_CHECKING

import typer
from typing_extensions import Annotated

from splitmybill.interface import CLISplitter
from splitmybill.parser import ParserType, determine_parser, get_parser

if TYPE_CHECKING:
    from pathlib import Path

app = typer.Typer(
    name="splitmybill",
    help="Automate splitting grocery bills with friends"
)


@app.command()
def cli(
    bill_path: Annotated[
        Path,
        typer.Argument(help="Path to the bill file.")
    ],
    parser: Annotated[
        ParserType | None,
        typer.Option(
            "--parser",
            "-p",
            help="Override automatic parser selection"
        )
    ] = None,
) -> None:
    """Start the CLI interface for bill splitting."""
    selected_parser = parser or determine_parser(bill_path)
    typer.echo(f"Using {selected_parser.value} parser")
    parser_obj = get_parser(
        parser_type=selected_parser,
        bill_path=bill_path
    )
    receipt_data = parser_obj.extract_bill()
    splitter = CLISplitter(
        receipt=receipt_data,
    )
    splitter.collect_split(receipt_data=receipt_data)
    splitter.display_split(split_data=split_data)
