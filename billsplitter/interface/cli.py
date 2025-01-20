from __future__ import annotations

from decimal import Decimal

from prettytable import PrettyTable

from billsplitter.data_model.receipt import ItemModel, ReceiptModel, TaxModel
from billsplitter.data_model.split import BillSplitModel
from billsplitter.interface.base import BaseInterface


class CLISplitter(BaseInterface):

    SPLIT_INSTRUCTIONS = ("\nEnter the split for each item as comma-separated "
                         "values with values indicating which person wants the item. "
                         "An empty split string indicates that all people want the item.\n")
    SPLIT_EXAMPLE = "It can be any combination of the following values: "
    TOTAL_STRING = "TOTAL"
    TAXES_STRING = "TAXES"
    CURRENCY_SYMBOL = "$"

    def __init__(
            self,
            **kwargs
    ):
        self.participants: list[str] = []
        self.valid_indices: list[int] = []

    def collect_split(
            self,
            receipt_data: ReceiptModel
        ) -> BillSplitModel:
        self.receipt_data = receipt_data
        self._collect_participants()
        self._display_split_instructions()
        return self._process_items(receipt_data)

    def display_split(self, split_data: BillSplitModel) -> None:
        self._display_common_items_table(split_data)
        self._display_separate_items_table(split_data)
        self._display_tax_breakdown_table(split_data)
        self._display_final_totals(split_data)
        self._display_validation_message(split_data)

    def _collect_participants(self) -> None:
        print("\nEnter participant names (empty line to finish):")
        while True:
            name = input("Name: ").strip()
            if not name:
                if len(self.participants) < 2:
                    print("Error: At least 2 participants are required")
                    continue
                break
            if name in self.participants:
                print(f"Error: {name} is already added")
                continue
            self.participants.append(name)

        # Update valid indices after collecting participants
        self.valid_indices = list(range(1, len(self.participants) + 1))

    def _display_split_instructions(self) -> None:
        """Display splitting instructions."""
        print("\nBill Split Instructions:")
        print("-" * 50)
        print(self.SPLIT_INSTRUCTIONS)
        print("Participants:")
        for idx, name in enumerate(self.participants, 1):
            print(f"{idx}. {name}")
        print("\nValid input formats:")
        print("- Empty input (press Enter): Everyone shares the item")
        print("- Single numbers: '1' or '1,2' or '1, 2'")
        print("- Consecutive numbers without commas: '12' means participants 1 and 2")
        print("-" * 50)

    def _process_items(self, receipt_data: ReceiptModel) -> BillSplitModel:
        common_items: list[ItemModel] = []
        separate_items: dict[str, list[ItemModel]] = {
            person: [] for person in self.participants
        }

        for item in receipt_data.items:
            split_indices = self._get_item_split(item)

            if split_indices == self.valid_indices:
                common_items.append(item)
            else:
                share_amount = item.subtotal / len(split_indices)
                for idx in split_indices:
                    person = self.participants[idx - 1]
                    # TODO: Figure out a more memory efficient way
                    item_share = item.model_copy(update={"subtotal": share_amount})
                    separate_items[person].append(item_share)
        split_data = BillSplitModel(
            common_items=common_items,
            separate_items=separate_items,
            participants=self.participants
        )
        split_data.calculate_shares(receipt_data)
        return split_data

    def _get_item_split(self, item: ItemModel) -> list[int]:
        """Get and validate split information for an item."""
        while True:
            prompt = self._format_item_prompt(item)
            split_str = input(prompt)

            if self._is_valid_split_str(split_str):
                return self._extract_split_string_indices(split_str)

            print("\nError: Invalid split format")
            self._display_split_format_help()

    def _format_item_prompt(self, item: ItemModel) -> str:
        """Format the prompt string for an item."""
        parts = [item.name]

        if item.quantity is not None:
            parts.append(f"x {item.quantity}")

        if item.unit_price is not None:
            parts.append(f"@ {self.CURRENCY_SYMBOL}{item.unit_price:.2f}")

        parts.append(f"(Total: {self.CURRENCY_SYMBOL}{item.subtotal:.2f})")
        return " ".join(parts) + ": "

    def _display_common_items_table(self, split_model: BillSplitModel) -> None:
        """Display table of common items."""
        if not split_model.common_items:
            print("\nNo common items")
            return

        table = PrettyTable()
        table.field_names = ["Common Items", "Price", "Per Person"]
        per_person = len(split_model.participants)

        for item in split_model.common_items:
            table.add_row([
                item.name,
                f"{self.CURRENCY_SYMBOL}{item.subtotal:.2f}",
                f"{self.CURRENCY_SYMBOL}{(item.subtotal / per_person):.2f}"
            ])

        print("\nCOMMON ITEMS:")
        print(table)

    def _display_separate_items_table(self, split_model: BillSplitModel) -> None:
        """Display table of separately split items."""
        if not any(split_model.separate_items.values()):
            print("\nNo separate items")
            return

        table = PrettyTable()
        table.field_names = ["Separate Items", *self.participants]

        # Get all unique items
        all_items = set()
        for items in split_model.separate_items.values():
            all_items.update(item.name for item in items)

        # Create rows
        for item_name in sorted(all_items):
            row = [item_name]
            for person in self.participants:
                amount = sum(
                    item.subtotal  # subtotal is already the share
                    for item in split_model.separate_items.get(person, [])
                    if item.name == item_name
                )
                row.append(f"{self.CURRENCY_SYMBOL}{amount:.2f}")
            table.add_row(row)

        print("\nSEPARATE ITEMS:")
        print(table)

    def _display_tax_breakdown_table(self, split_model: BillSplitModel) -> None:
        """Display tax breakdown table."""
        table = PrettyTable()
        table.field_names = ["Person", "Pretax Amount", "Tax Share", "Total"]

        # Add row for each person
        for person in self.participants:
            table.add_row([
                person,
                f"{self.CURRENCY_SYMBOL}{split_model.participant_shares[person]:.2f}",
                f"{self.CURRENCY_SYMBOL}{split_model.tax_shares[person]:.2f}",
                f"{self.CURRENCY_SYMBOL}{split_model.total_shares[person]:.2f}"
            ])

        # Add total row
        total_pretax = sum(split_model.participant_shares.values())
        total_tax = sum(split_model.tax_shares.values())
        total_final = sum(split_model.total_shares.values())

        table.add_row([
            "TOTAL",
            f"{self.CURRENCY_SYMBOL}{total_pretax:.2f}",
            f"{self.CURRENCY_SYMBOL}{total_tax:.2f}",
            f"{self.CURRENCY_SYMBOL}{total_final:.2f}"
        ])

        print("\nTAX BREAKDOWN:")
        print(table)

    def _display_final_totals(self, split_model: BillSplitModel) -> None:
        """Display final amount owed by each person."""
        print("\nFINAL TOTALS:")
        for person in self.participants:
            total = split_model.total_shares[person]
            print(f"{person}: {self.CURRENCY_SYMBOL}{total:.2f}")

    def _display_validation_message(self, split_model: BillSplitModel) -> None:
        """Display validation message comparing against receipt total."""
        total_bill = sum(split_model.total_shares.values())

        if abs(total_bill - self.receipt_data.total) > Decimal("0.01"):
            print("\nWARNING: Total bill amount differs from receipt total")
            print(f"Calculated total: {self.CURRENCY_SYMBOL}{total_bill:.2f}")
            print(f"Receipt total: {self.CURRENCY_SYMBOL}{self.receipt_data.total:.2f}")

    def _is_valid_split_str(self, split_str: str) -> bool:
        """Validate the split string format."""
        if split_str == "":
            return True

        try:
            indices = self._extract_split_string_indices(split_str)
            return bool(indices) and all(idx in self.valid_indices for idx in indices)
        except ValueError:
            return False

    def _extract_split_string_indices(self, split_str: str) -> list[int]:
        """Extract participant indices from the split string."""
        if split_str == "":
            return self.valid_indices

        # Handle both comma-separated and non-comma-separated inputs
        if "," in split_str:
            parts = [p.strip() for p in split_str.split(",")]
        else:
            parts = list(split_str.replace(" ", ""))

        try:
            indices = [int(part) for part in parts if part]
            return sorted(set(indices))  # Remove duplicates and sort
        except ValueError as e:
            raise ValueError("Invalid split string format") from e

    def _display_split_format_help(self) -> None:
        """Display help message for split format."""
        print("\nPlease enter:")
        print("- Nothing (press Enter) if everyone shares the item")
        print("- Numbers corresponding to participants (e.g., '1,2' or '12')")
        print(f"- Valid participant numbers are: {self.valid_indices}\n")
