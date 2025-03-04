from __future__ import annotations

import os
from pathlib import Path

import typer
from typing_extensions import Annotated

from splitmybill.interface import CLISplitter, SmartCLISplitter
from splitmybill.interface.telegram_bot import TelegramSplitter
from splitmybill.parser import ParserType, determine_parser, get_parser

app = typer.Typer(
    name="splitmybill",
    help="Automate splitting grocery bills with friends"
)


@app.command("smartcli")
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


@app.command("telegram")
def telegram_bot(
    telegram_token: Annotated[
        str | None,
        typer.Option(
            "--telegram-token",
            envvar="TELEGRAM_BOT_TOKEN",
            help="Telegram Bot Token"
        )
    ] = None,
    anthropic_key: Annotated[
        str | None,
        typer.Option(
            "--anthropic-key",
            envvar="ANTHROPIC_API_KEY",
            help="Anthropic API Key"
        )
    ] = None,
) -> None:
    """Start the Telegram bot interface for bill splitting."""
    if not telegram_token:
        raise typer.BadParameter(
            "Telegram bot token is required. Set it via --telegram-token or TELEGRAM_BOT_TOKEN environment variable."
        )
    if not anthropic_key:
        raise typer.BadParameter(
            "Anthropic API key is required. Set it via --anthropic-key or ANTHROPIC_API_KEY environment variable."
        )

    typer.echo("Starting Telegram bot...")
    bot = TelegramSplitter(
        token=telegram_token,
        api_key=anthropic_key
    )
    bot.run()



if __name__ == "__main__":
    telegram_bot(
        # bill_path="data/receipts/images/costco_02012025.jpg",
        anthropic_key=os.environ["ANTHROPIC_API_KEY"],
        telegram_token=os.environ["TELEGRAM_BOT_TOKEN"]
    )
