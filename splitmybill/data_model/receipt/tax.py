# ruff: noqa: G004, TCH003

from __future__ import annotations

import logging
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)


class TaxModel(BaseModel):
    """A data model representing tax and fee items in a receipt.

    This model captures various types of taxes and fees that might appear on a receipt, such as sales
    tax, service charges, or other additional fees.

    Attributes:
        name: The name or description of the tax/fee as it appears on the receipt.
        rate: The tax rate as a percentage (e.g., 8 for 8% tax). Optional.
        total: The total amount of this tax or fee in the receipt's currency.
        metadata: Additional tax-related information like jurisdiction or tax category.
    """
    name: str = Field(
        description=(
            "The name or description of the tax/fee or discount as it appears on the receipt "
            "(e.g., 'Sales Tax', 'Service Fee', 'Discount', 'Membership Discount')"
        )
    )
    rate: int | None = Field(
        default=None,
        description=(
            "The tax rate as a percentage (e.g., 8 for 8% tax). Should be between 0 and 100. "
            "Optional as some fees might not have a rate."
        )
    )
    total: Decimal = Field(
        description=("The total amount of this tax or fee in the receipt's currency. "
                     "This may be negative for discounts and offers.")
    )
    metadata: dict | None = Field(
        default=None,
        description=(
            "Additional tax-related information like jurisdiction, tax category, or any "
            "receipt-specific details"
        )
    )

    @model_validator(mode="after")
    def validate_tax_fields(self) -> None:
        """Validate tax rate and amount fields.

        Validates that:
            - Tax rate (if provided) is between 0 and 100
            - Total amount is not negative

        Returns:
            The validated model instance.
        """
        if self.rate is not None and not 0 <= self.rate <= 100:  # noqa: PLR2004
            logger.warning(
                f"Tax '{self.name}' has invalid rate: {self.rate}. "
                "Rate should be between 0 and 1"
            )

        if self.total < Decimal(0):
            logger.warning(f"Tax '{self.name}' has negative amount: {self.total}")

        return self
