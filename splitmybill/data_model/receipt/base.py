# ruff: noqa: TCH001, TCH003
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from splitmybill.data_model.receipt.item import ItemModel
from splitmybill.data_model.receipt.tax import TaxModel


class ReceiptModel(BaseModel):
    """A data model representing a complete receipt structure.

    This model represents a complete receipt, containing all items purchased, associated taxes and fees,
    and total amounts. It captures the full structure of a receipt as you would see it from a store or
    service provider.

    Attributes:
        items: List of individual items on the receipt with details like name, quantity, price.
        taxes_and_fees: List of all taxes and fees applied to the receipt.
        subtotal: The sum of all item costs before taxes and fees are applied.
        total: The final total amount including all items, taxes, and fees.
        metadata: Additional receipt information like store name, date, receipt number.
    """
    items: list[ItemModel] | None = Field(
        default=None,
        description="List of individual items on the receipt. Each item contains details like name, "
        "quantity, price, etc."
    )
    taxes_and_fees: list[TaxModel] | None = Field(
        default=None,
        description="List of all taxes and fees applied to the receipt, such as sales tax, service "
        "charges, etc."
    )
    subtotal: Decimal | None = Field(
        default=None,
        description="The sum of all item costs before taxes and fees are applied"
    )
    total: Decimal | None = Field(
        default=None,
        description="The final total amount including all items, taxes, and fees"
    )
    metadata: dict | None = Field(
        default=None,
        description="Additional receipt information like store name, date, receipt number, or any "
        "other relevant details"
    )
