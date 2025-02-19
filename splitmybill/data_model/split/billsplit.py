from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from splitmybill.data_model.receipt import ItemModel, ReceiptModel


class BillSplitModel(BaseModel):
    """A model representing how a bill is split between participants.

    This model captures both items that are shared equally among all participants and items that are
    split between specific participants. It also handles the calculation of individual shares including
    tax distribution.

    Attributes:
        common_items: Items that are split equally among all participants.
        separate_items: Items assigned to specific participants.
        participants: List of all participants involved in splitting the bill.
        _participant_shares: Internal cache of pre-tax amount each participant owes.
        _tax_shares: Internal cache of tax amount each participant owes.
    """
    common_items: list[ItemModel] | None = Field(
        default=None,
        description="Items that are split equally among all participants (e.g., shared appetizers)"
    )
    separate_items: dict[str, list[ItemModel]] | None = Field(
        default=None,
        description="Items assigned to specific participants, mapping participant names to their "
        "individual items"
    )
    participants: list[str] = Field(
        default_factory=list,
        description="List of all participants involved in splitting the bill"
    )

    _participant_shares: dict[str, Decimal] | None = None
    _tax_shares: dict[str, Decimal] | None = None
    def calculate_shares(
            self,
            receipt_data: ReceiptModel
    ) -> None:
        """Calculate both pre-tax and tax shares for all participants.

        This method calculates each participant's share of both the pre-tax amount and the taxes/fees.
        Tax shares are calculated proportionally based on each person's share of the pre-tax total.

        Args:
            receipt_data: The complete receipt data including taxes and fees.
        """
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
        """Calculate pre-tax shares for each participant.

        This method calculates each participant's share of the pre-tax total by:
        1. Splitting common items equally among all participants
        2. Adding individual items from separate_items to each person's total
        """
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
        """Get pre-tax shares per participant.

        Returns:
            A dictionary mapping participant names to their pre-tax share amounts.
        """
        if self._participant_shares is None:
            self._calculate_pretax_shares()
        return self._participant_shares

    @property
    def tax_shares(self) -> dict[str, Decimal]:
        """Get tax shares per participant.

        Returns:
            A dictionary mapping participant names to their share of taxes and fees.

        Raises:
            ValueError: If calculate_shares() hasn't been called yet.
        """
        if self._tax_shares is None:
            raise ValueError("Tax shares not calculated. Call calculate_shares first.")
        return self._tax_shares

    @property
    def total_shares(self) -> dict[str, Decimal]:
        """Get total shares (including tax) per participant.

        Returns:
            A dictionary mapping participant names to their total amount owed (pre-tax + tax).

        Raises:
            ValueError: If calculate_shares() hasn't been called yet.
        """
        if self._participant_shares is None or self._tax_shares is None:
            raise ValueError("Shares not calculated. Call calculate_shares first.")

        return {
            person: self._participant_shares[person] + self._tax_shares[person]
            for person in self.participants
        }


class LLMSplitResponse(BaseModel):
    """A response model for LLM-based bill splitting that supports iterative clarification.

    This model is designed to handle both complete and partial bill splits, allowing for iterative
    refinement through clarification questions when needed. It helps manage the conversation flow
    between the LLM and the user when splitting instructions are ambiguous or incomplete.

    Attributes:
        split_result: The current state of the bill split, which may be partial.
        needs_clarification: Whether additional information is needed to complete the split.
        clarification_question: The specific question to ask the user when clarification is needed.
    """

    split_result: BillSplitModel = Field(
        description="The bill split result, which can be partial. Must contain:\n"
        "- All provided participants\n"
        "- Items split so far, categorized as either:\n"
        "  a) common_items: List of items shared equally by all participants\n"
        "  b) separate_items: Dict mapping participant names to their individual items\n"
        "Even if clarification is needed, include all splits that could be determined"
    )

    needs_clarification: bool = Field(
        default=False,
        description="Set to True if additional information is needed to complete the split.\n"
        "Common reasons for clarification:\n"
        "- Some items in the receipt weren't mentioned in the splitting instructions\n"
        "- Ambiguous instructions about how to split specific items\n"
        "- Missing participant information for certain splits"
    )

    clarification_question: str | None = Field(
        default=None,
        description="When needs_clarification is True, provide a clear, specific question about what "
        "additional information is needed.\nThe question should:\n"
        "- Reference specific items or list of items or splits that need clarification\n"
        "- Be phrased in a way that prompts a clear, actionable response\n"
        "- Only ask about information that wasn't provided or was ambiguous in the original "
        "instructions\n"
        'Example: "I see there\'s a soda ($2.50) on the receipt. How should that be split between '
        'the participants?"'
    )

    @property
    def is_complete(self) -> bool:
        """Check if the split response is complete and needs no further clarification.

        Returns:
            bool: True if the split is complete, False if clarification is needed.
        """
        return not self.needs_clarification
