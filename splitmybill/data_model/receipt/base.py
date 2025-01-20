# ruff: noqa: TCH001
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from splitmybill.data_model.receipt.item import ItemModel
from splitmybill.data_model.receipt.tax import TaxModel


class ReceiptModel(BaseModel):
    """Data model representing a receipt structure.

    Contains lists of items and their associated taxes/fees.
    """
    items: list[ItemModel] | None = None
    taxes_and_fees: list[TaxModel] | None = None
    subtotal: Decimal | None = None
    total: Decimal | None = None

    metadata: dict | None = None
