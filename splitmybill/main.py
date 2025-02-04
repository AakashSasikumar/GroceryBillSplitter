from __future__ import annotations

import os
from pathlib import Path

import typer
from typing_extensions import Annotated

from splitmybill.interface import CLISplitter, SmartCLISplitter
from splitmybill.parser import ParserType, determine_parser, get_parser

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
    anthropic_key: Annotated[
        str | None,
        typer.Option(
            "--anthropic-key",
            envvar="ANTHROPIC_API_KEY",
        )
    ] = None,
) -> None:
    """Start the CLI interface for bill splitting."""
    selected_parser = parser or determine_parser(bill_path)
    typer.echo(f"Using {selected_parser.value} parser")
    parser_obj = get_parser(
        parser_type=selected_parser,
        bill_path=bill_path,
        api_key=anthropic_key
    )
    receipt_data = parser_obj.extract_bill()
    splitter = SmartCLISplitter(
        receipt=receipt_data,
        api_key=anthropic_key
    )
    split_data = splitter.collect_split(receipt_data=receipt_data)
    splitter.display_split(split_data=split_data)


if __name__ == "__main__":
    cli(
        bill_path="data/receipts/images/costco_02012025.jpg",
        anthropic_key=os.environ["ANTHROPIC_API_KEY"]
    )
