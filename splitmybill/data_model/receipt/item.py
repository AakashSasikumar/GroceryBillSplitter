# ruff: noqa: G004

from __future__ import annotations

import logging
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class ItemModel(BaseModel):
    """Data model representing an individual item in a receipt."""
    name: str = Field(
        description="The product name or description of the item as it appears on the receipt"
    )
    quantity: int | Decimal | None = Field(
        default=None,
        description="The number of units purchased. If omitted, the quantity will be assumed to be 1"
    )
    unit_price: Decimal | None = Field(
        default=None,
        description="The price per unit of the item."
    )
    subtotal: Decimal = Field(
        description="The total cost for this line item (quantity * unit_price, or the final price if quantity/unit price not available)"
    )
    metadata: dict | None = Field(
        default=None,
        description="Additional item details like weight units, discounts applied, item category, or any other receipt-specific information"
    )

    @model_validator(mode="after")
    def validate_item_fields(self) -> None:
        if self.quantity is not None and self.quantity <= 0:
            logger.warning(f"Item '{self.name}' has invalid quantity: {self.quantity}")

        return self
