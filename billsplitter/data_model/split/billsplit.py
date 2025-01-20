from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from billsplitter.data_model.receipt import ItemModel, ReceiptModel


class BillSplitModel(BaseModel):
    common_items: list[ItemModel] | None = None
    separate_items: dict[str, list[ItemModel]] | None = None
    participants: list[str] = []

    _participant_shares: dict[str, Decimal] | None = None
    _tax_shares: dict[str, Decimal] | None = None

    def calculate_shares(
            self,
            receipt_data: ReceiptModel
    ) -> None:
        self._calculate_pretax_shares()

        # Calculate tax shares
        total_pretax = sum(self._participant_shares.values())
        total_tax = sum(tax.total for tax in receipt_data.taxes_and_fees)
        # Calculate proportional tax shares
        self._tax_shares = {
            person: (self._participant_shares[person] / total_pretax) * total_tax
            for person in self.participants
        }

    def _calculate_pretax_shares(self) -> None:
        """Calculate pre-tax shares for each participant."""
        self._participant_shares = {person: Decimal(0) for person in self.participants}

        # Add shares from common items
        if self.common_items:
            common_per_person = sum(
                item.subtotal for item in self.common_items
            ) / len(self.participants)

            for person in self.participants:
                self._participant_shares[person] += common_per_person
        # Add shares from separate items
        if self.separate_items:
            for person, items in self.separate_items.items():
                self._participant_shares[person] += sum(
                    item.subtotal for item in items
                )

    @property
    def participant_shares(self) -> dict[str, Decimal]:
        """Get pre-tax shares per participant."""
        if self._participant_shares is None:
            self._calculate_pretax_shares()
        return self._participant_shares

    @property
    def tax_shares(self) -> dict[str, Decimal]:
        """Get tax shares per participant."""
        if self._tax_shares is None:
            raise ValueError("Tax shares not calculated. Call calculate_shares first.")
        return self._tax_shares

    @property
    def total_shares(self) -> dict[str, Decimal]:
        """Get total shares (including tax) per participant."""
        if self._participant_shares is None or self._tax_shares is None:
            raise ValueError("Shares not calculated. Call calculate_shares first.")

        return {
            person: self._participant_shares[person] + self._tax_shares[person]
            for person in self.participants
        }
