from __future__ import annotations

from decimal import Decimal

from prettytable import PrettyTable

from billsplitter.data_model.receipt import ItemModel, ReceiptModel, TaxModel
from billsplitter.splitter.base import BaseSplitter


class CLIConstants:
    """Constants used in the CLI for splitting receipts.

    This class contains the constants used to display in the CLI.
    """

    SPLIT_INSTRUCTIONS = ("\nEnter the split for each item as comma-separated "
                         "values with values indicating which person wants the item. "
                         "An empty split string indicates that all people want the item.\n")
    SPLIT_EXAMPLE = "It can be any combination of the following values: "
    TOTAL_STRING = "TOTAL"
    TAXES_STRING = "TAXES"
    CURRENCY_SYMBOL = "$"


class CLISplitter(BaseSplitter):
    def __init__(
            self,
            receipt: ReceiptModel,
            participants: list[str],
            **kwargs
    ):
        super().__init__(
            receipt,
            participants
        )
        self.valid_indices = list(range(1, len(participants) + 1))

    def split_bill(
            self
        ):
        self._display_split_instructions()
        common_split, separate_split = self._process_items()
        self._display_totals(
            common_split,
            separate_split
        )

    def _process_items(self) -> tuple[dict[str, Decimal], dict[str, dict[str, Decimal]]]:
        common_split: dict[str, Decimal] = {}
        separate_split = {person: {} for person in self.participants}

        for item in self.receipt.items:
            split_indices = self._get_item_split(item)

            if split_indices == self.valid_indices:
                common_split[item.name] = item.subtotal
            else:
                split_share = item.subtotal / len(split_indices)
                for idx in split_indices:
                    person = self.participants[idx - 1]
                    separate_split[person][item.name] = split_share
        return common_split, separate_split

    def _get_item_split(self, item: ItemModel) -> list[int]:
        """Get and validate split information for an item."""
        while True:
            quantity_str = f" x {item.quantity}" if item.quantity is not None else ""
            unit_price_str = (f" @ {CLIConstants.CURRENCY_SYMBOL}{item.unit_price}"
                            if item.unit_price is not None else "")

            prompt = (f"{item.name}{quantity_str}{unit_price_str} "
                     f"(Total: {CLIConstants.CURRENCY_SYMBOL}{item.subtotal}): ")

            split_str = input(prompt)

            if self._is_valid_split_str(split_str):
                return self._extract_split_string_indices(split_str)

            print("Invalid split string. Please enter a valid split string.")

    def _display_totals(
            self,
            common_split: dict[str, Decimal],
            separate_split: dict[str, dict[str, Decimal]]
    ):
        common_total = sum(common_split.values())
        common_per_person = common_total / len(self.participants)

        pretax_totals = {}
        for person in self.participants:
            separate_total = sum(separate_split[person].values())
            pretax_totals[person] = separate_total + common_per_person

        total_pretax = sum(pretax_totals.values())
        total_tax = sum(tax.total for tax in self.receipt.taxes_and_fees)

        if total_pretax <= Decimal(0):
            msg = ("Invalid receipt: Total pretax amount is 0. "
                  "Cannot calculate proportional taxes with zero total.")
            raise ValueError(msg)

        for person in self.participants:
            tax_share = (pretax_totals[person] / total_pretax) * total_tax
            separate_split[person][CLIConstants.TAXES_STRING] = tax_share
            separate_split[person][CLIConstants.TOTAL_STRING] = (
                pretax_totals[person] + tax_share
            )
        self._display_split_details(
            common_split,
            separate_split,
            pretax_totals,
            total_tax
        )

    def _display_split_details(
            self,
            common_split: dict[str, Decimal],
            separate_split: dict[str, dict[str, Decimal]],
            person_pretax_totals: dict[str, Decimal],
            total_tax: Decimal
    ) -> None:
        """Display detailed split information including tax breakdown."""
        # Display common items
        common_table = self._create_common_items_table(common_split)
        print("\nCOMMON ITEMS:")
        print(common_table)

        # Display separate items
        separate_table = self._create_separate_items_table(separate_split)
        print("\nSEPARATE ITEMS:")
        print(separate_table)

        # Display tax breakdown
        tax_table = self._create_tax_breakdown_table(
            person_pretax_totals,
            separate_split,
            total_tax
        )
        print("\nTAX BREAKDOWN:")
        print(tax_table)

        # Display final totals
        total_bill = self._display_final_totals(separate_split)

        # Validate against receipt subtotal
        if abs(total_bill - (self.receipt.total)) > Decimal("0.01"):
            print("\nWARNING: Total bill amount differs from receipt total")
            print(f"Calculated total: {CLIConstants.CURRENCY_SYMBOL}{total_bill:.2f}")
            print(f"Receipt total: {CLIConstants.CURRENCY_SYMBOL}"
                  f"{(self.receipt.total):.2f}")

    def _create_tax_breakdown_table(
            self,
            person_pretax_totals: dict[str, Decimal],
            separate_split: dict[str, dict[str, Decimal]],
            total_tax: Decimal
    ) -> PrettyTable:
        """Create table showing tax breakdown per person."""
        tax_table = PrettyTable()
        tax_table.field_names = ["Person", "Pretax Amount", "Tax Share", "Total"]

        for person in self.participants:
            pretax = person_pretax_totals[person]
            tax_share = separate_split[person][CLIConstants.TAXES_STRING]
            total = separate_split[person][CLIConstants.TOTAL_STRING]

            tax_table.add_row([
                person,
                f"{CLIConstants.CURRENCY_SYMBOL}{pretax:.2f}",
                f"{CLIConstants.CURRENCY_SYMBOL}{tax_share:.2f}",
                f"{CLIConstants.CURRENCY_SYMBOL}{total:.2f}"
            ])

        # Add total row
        total_pretax = sum(person_pretax_totals.values())
        total_final = sum(split[CLIConstants.TOTAL_STRING]
                         for split in separate_split.values())

        tax_table.add_row([
            "TOTAL",
            f"{CLIConstants.CURRENCY_SYMBOL}{total_pretax:.2f}",
            f"{CLIConstants.CURRENCY_SYMBOL}{total_tax:.2f}",
            f"{CLIConstants.CURRENCY_SYMBOL}{total_final:.2f}"
        ])

        return tax_table

    def _create_common_items_table(self, common_split: dict[str, Decimal]) -> PrettyTable:
        """Create table for common items."""
        table = PrettyTable()
        table.field_names = ["Common Items", "Price"]
        for item, price in common_split.items():
            table.add_row([item, f"{CLIConstants.CURRENCY_SYMBOL}{price:.2f}"])
        return table

    def _create_separate_items_table(
            self,
            separate_split: dict[str, dict[str, Decimal]]
    ) -> PrettyTable:
        """Create table for separately split items."""
        table = PrettyTable()
        table.field_names = ["Separate Items", *self.participants]

        all_items = set()
        for person_items in separate_split.values():
            all_items.update(k for k in person_items.keys() 
                           if k not in {CLIConstants.TOTAL_STRING, CLIConstants.TAXES_STRING})

        for item in sorted(all_items):
            row = [item]
            for person in self.participants:
                amount = separate_split[person].get(item, Decimal(0))
                row.append(f"{CLIConstants.CURRENCY_SYMBOL}{amount:.2f}")
            table.add_row(row)
        return table

    def _display_final_totals(
            self,
            separate_split: dict[str, dict[str, Decimal]]
    ) -> Decimal:
        """Display final totals for each person and return total bill amount."""
        total_bill = Decimal(0)
        for person in self.participants:
            total = separate_split[person][CLIConstants.TOTAL_STRING]
            total_bill += total
            print(f"{person}: {CLIConstants.CURRENCY_SYMBOL}{total:.2f}")
        print(f"\nTotal Bill: {CLIConstants.CURRENCY_SYMBOL}{total_bill:.2f}")
        return total_bill

    def _is_valid_split_str(self, split_str: str) -> bool:
        """Validate split string input."""
        if split_str == "":
            return True

        try:
            indices = self._extract_split_string_indices(split_str)
            return all(index in self.valid_indices for index in indices)
        except ValueError:
            return False

    def _extract_split_string_indices(self, split_str: str) -> list[int]:
        """Extract indices from split string."""
        if split_str == "":
            return self.valid_indices

        if "," not in split_str:
            return [int(index) for index in list(split_str)]

        return [int(index) for index in split_str.split(",")]

    def _display_split_instructions(self) -> None:
        """Display instructions for splitting items."""
        print(CLIConstants.SPLIT_INSTRUCTIONS)
        print(CLIConstants.SPLIT_EXAMPLE, self.valid_indices)
