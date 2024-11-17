# ruff: noqa: TCH001
from __future__ import annotations

from pydantic import BaseModel

from billsplitter.data_model.receipt.item import ItemModel
from billsplitter.data_model.receipt.tax import TaxModel


class ReceiptModel(BaseModel):
    """Data model representing a receipt structure.

    Contains lists of items and their associated taxes/fees.
    """
    items: list[ItemModel]
    taxes_and_fees: list[TaxModel]
    metadata: dict
    subtotal: float
